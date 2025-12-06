from functools import partialmethod
from itertools import chain

from django.db import NotSupportedError
from django.db.models.fields.json import (
    ContainedBy,
    DataContains,
    HasAnyKeys,
    HasKey,
    HasKeyLookup,
    HasKeys,
    JSONExact,
    KeyTransform,
    KeyTransformExact,
    KeyTransformIn,
    KeyTransformIsNull,
    KeyTransformNumericLookupMixin,
)

from django_mongodb_backend.lookups import builtin_lookup_expr, builtin_lookup_path
from django_mongodb_backend.query_utils import process_lhs, process_rhs


def valid_path_key_name(key_name):
    # A lookup can use path syntax (field.subfield) unless it contains a dollar
    # sign or period.
    return not key_name.startswith("-") and not any(char in key_name for char in ("$", "."))


def build_json_mql_path(lhs, key_transforms, as_expr=False):
    # Build the MQL path using the collected key transforms.
    if not as_expr:
        return ".".join(chain([lhs], key_transforms))
    result = lhs
    for key in key_transforms:
        get_field = {"$getField": {"input": result, "field": key}}
        # Handle array indexing if the key is a digit. If key is something
        # like '001', it's not an array index despite isdigit() returning True.
        try:
            int(key)
            is_digit = str(int(key)) == key
        except ValueError:
            is_digit = False
        if is_digit:
            result = {
                "$cond": {
                    "if": {"$isArray": result},
                    "then": {"$arrayElemAt": [result, int(key)]},
                    "else": get_field,
                }
            }
        else:
            result = get_field
    return result


def contained_by(self, compiler, connection, as_expr=False):  # noqa: ARG001
    raise NotSupportedError("contained_by lookup is not supported on this database backend.")


def data_contains(self, compiler, connection, as_expr=False):  # noqa: ARG001
    raise NotSupportedError("contains lookup is not supported on this database backend.")


def _has_key_predicate(path, root_column=None, negated=False, as_expr=False):
    """Return MQL to check for the existence of `path`."""
    if not as_expr:
        return {path: {"$exists": not negated}}
    result = {
        "$and": [
            # The path must exist (i.e. not be "missing").
            {"$ne": [{"$type": path}, "missing"]},
            # If the JSONField value is None, an additional check for not null
            # is needed since $type returns null instead of "missing".
            {"$ne": [root_column, None]},
        ]
    }
    if negated:
        result = {"$not": result}
    return result


def has_key_lookup(self, compiler, connection, as_expr=False):
    """Return MQL to check for the existence of a key."""
    rhs = self.rhs
    lhs = process_lhs(self, compiler, connection, as_expr=as_expr)
    if not isinstance(rhs, (list, tuple)):
        rhs = [rhs]
    paths = []
    # Transform any "raw" keys into KeyTransforms to allow consistent handling
    # in the code that follows.
    for key in rhs:
        rhs_json_path = key if isinstance(key, KeyTransform) else KeyTransform(key, self.lhs)
        paths.append(rhs_json_path.as_mql(compiler, connection, as_expr=as_expr))
    keys = []
    for path in paths:
        keys.append(_has_key_predicate(path, lhs, as_expr=as_expr))
    if self.mongo_operator is None:
        return keys[0]
    return {self.mongo_operator: keys}


@property
def has_key_lookup_can_use_path(self):
    rhs = [self.rhs] if not isinstance(self.rhs, (list, tuple)) else self.rhs
    return self.is_simple_column and all(valid_path_key_name(key) for key in rhs)


_process_rhs = JSONExact.process_rhs


def json_exact_process_rhs(self, compiler, connection):
    """Skip JSONExact.process_rhs()'s conversion of None to "null"."""
    return (
        super(JSONExact, self).process_rhs(compiler, connection)
        if connection.vendor == "mongodb"
        else _process_rhs(self, compiler, connection)
    )


def key_transform(self, compiler, connection, as_expr=False):
    """
    Return MQL for this KeyTransform (JSON path).

    JSON paths cannot always be represented simply as $var.key1.key2.key3 due
    to possible array types. Therefore, indexing arrays requires the use of
    `arrayElemAt`. Additionally, $cond is necessary to verify the type before
    performing the operation.
    """
    key_transforms = [self.key_name]
    previous = self.lhs
    # Collect all key transforms in order.
    while isinstance(previous, KeyTransform):
        key_transforms.insert(0, previous.key_name)
        previous = previous.lhs
    lhs_mql = previous.as_mql(compiler, connection, as_expr=as_expr)
    return build_json_mql_path(lhs_mql, key_transforms, as_expr=as_expr)


@property
def key_transform_is_simple_column(self):
    previous = self
    while isinstance(previous, KeyTransform):
        if not valid_path_key_name(previous.key_name):
            return False
        previous = previous.lhs
    return previous.is_simple_column


def key_transform_exact_path(self, compiler, connection):
    lhs_mql = process_lhs(self, compiler, connection)
    return {
        "$and": [
            builtin_lookup_path(self, compiler, connection),
            _has_key_predicate(lhs_mql, None),
        ]
    }


def key_transform_in_expr(self, compiler, connection):
    """
    Return MQL to check if a JSON path exists and that its values are in the
    set of specified values (rhs).
    """
    lhs_mql = process_lhs(self, compiler, connection, as_expr=True)
    # Traverse to the root column.
    previous = self.lhs
    while isinstance(previous, KeyTransform):
        previous = previous.lhs
    root_column = previous.as_mql(compiler, connection, as_expr=True)
    value = process_rhs(self, compiler, connection, as_expr=True)
    # Construct the expression to check if lhs_mql values are in rhs values.
    expr = connection.mongo_expr_operators[self.lookup_name](lhs_mql, value)
    return {"$and": [_has_key_predicate(lhs_mql, root_column, as_expr=True), expr]}


def key_transform_is_null_expr(self, compiler, connection):
    """
    Return MQL to check the nullability of a key.

    If `isnull=True`, the query matches objects where the key is missing or the
    root column is null. If `isnull=False`, the query negates the result to
    match objects where the key exists.

    Reference: https://code.djangoproject.com/ticket/32252
    """
    lhs_mql = process_lhs(self, compiler, connection, as_expr=True)
    rhs_mql = process_rhs(self, compiler, connection, as_expr=True)
    # Get the root column.
    previous = self.lhs
    while isinstance(previous, KeyTransform):
        previous = previous.lhs
    root_column = previous.as_mql(compiler, connection, as_expr=True)
    return _has_key_predicate(lhs_mql, root_column, negated=rhs_mql, as_expr=True)


def key_transform_is_null_path(self, compiler, connection):
    """Return MQL to check the nullability of a key using $exists."""
    lhs_mql = process_lhs(self, compiler, connection)
    rhs_mql = process_rhs(self, compiler, connection)
    return _has_key_predicate(lhs_mql, None, negated=rhs_mql)


def key_transform_numeric_lookup_mixin_expr(self, compiler, connection):
    """
    Return MQL to check if the field exists (i.e., is not "missing" or "null")
    and that the field matches the given numeric lookup expression.
    """
    expr = builtin_lookup_expr(self, compiler, connection)
    lhs = process_lhs(self, compiler, connection, as_expr=True)
    # Check if the type of lhs is not "missing" or "null".
    not_missing_or_null = {"$not": {"$in": [{"$type": lhs}, ["missing", "null"]]}}
    return {"$and": [expr, not_missing_or_null]}


def register_json_field():
    ContainedBy.as_mql = contained_by
    DataContains.as_mql = data_contains
    HasAnyKeys.mongo_operator = "$or"
    HasKey.mongo_operator = None
    HasKeyLookup.as_mql_expr = partialmethod(has_key_lookup, as_expr=True)
    HasKeyLookup.as_mql_path = partialmethod(has_key_lookup, as_expr=False)
    HasKeyLookup.can_use_path = has_key_lookup_can_use_path
    HasKeys.mongo_operator = "$and"
    JSONExact.process_rhs = json_exact_process_rhs
    KeyTransform.as_mql_expr = partialmethod(key_transform, as_expr=True)
    KeyTransform.as_mql_path = partialmethod(key_transform, as_expr=False)
    KeyTransform.can_use_path = key_transform_is_simple_column
    KeyTransform.is_simple_column = key_transform_is_simple_column
    KeyTransformExact.as_mql_path = key_transform_exact_path
    KeyTransformIn.as_mql_expr = key_transform_in_expr
    KeyTransformIsNull.as_mql_expr = key_transform_is_null_expr
    KeyTransformIsNull.as_mql_path = key_transform_is_null_path
    KeyTransformNumericLookupMixin.as_mql_expr = key_transform_numeric_lookup_mixin_expr
