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

from ..lookups import builtin_lookup_expr, builtin_lookup_path
from ..query_utils import is_simple_column, is_simple_expression, process_lhs, process_rhs


def build_json_mql_path(lhs, key_transforms, as_path=False):
    # Build the MQL path using the collected key transforms.
    if as_path and lhs:
        return ".".join(chain([lhs], key_transforms))
    result = lhs
    for key in key_transforms:
        get_field = {"$getField": {"input": result, "field": key}}
        # Handle array indexing if the key is a digit. If key is something
        # like '001', it's not an array index despite isdigit() returning True.
        if key.isdigit() and str(int(key)) == key:
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


def contained_by(self, compiler, connection, as_path=False):  # noqa: ARG001
    raise NotSupportedError("contained_by lookup is not supported on this database backend.")


def data_contains(self, compiler, connection, as_path=False):  # noqa: ARG001
    raise NotSupportedError("contains lookup is not supported on this database backend.")


def _has_key_predicate(path, root_column=None, negated=False, as_path=False):
    """Return MQL to check for the existence of `path`."""
    if as_path:
        # if not negated:
        return {path: {"$exists": not negated}}
        # return {"$and": [{path: {"$exists": True}}, {path: {"$ne": None}}]}
        # return {"$or": [{path: {"$exists": False}}, {path: None}]}
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


def has_key_check_simple_expression(self):
    return is_simple_expression(self) and all("." not in v for v in self.rhs)


def has_key_lookup(self, compiler, connection, as_path=False):
    """Return MQL to check for the existence of a key."""
    rhs = self.rhs
    if not isinstance(rhs, (list, tuple)):
        rhs = [rhs]
    lhs = process_lhs(self, compiler, connection, as_path=as_path)
    paths = []
    # Transform any "raw" keys into KeyTransforms to allow consistent handling
    # in the code that follows.
    for key in rhs:
        rhs_json_path = key if isinstance(key, KeyTransform) else KeyTransform(key, self.lhs)
        paths.append(rhs_json_path.as_mql(compiler, connection, as_path=as_path))
    keys = []
    for path in paths:
        keys.append(_has_key_predicate(path, lhs, as_path=as_path))

    return keys[0] if self.mongo_operator is None else {self.mongo_operator: keys}


def has_key_lookup_path(self, compiler, connection):
    return has_key_lookup(self, compiler, connection, as_path=True)


def has_key_lookup_expr(self, compiler, connection):
    return has_key_lookup(self, compiler, connection, as_path=False)


_process_rhs = JSONExact.process_rhs


def json_exact_process_rhs(self, compiler, connection):
    """Skip JSONExact.process_rhs()'s conversion of None to "null"."""
    return (
        super(JSONExact, self).process_rhs(compiler, connection)
        if connection.vendor == "mongodb"
        else _process_rhs(self, compiler, connection)
    )


def key_transform_path(self, compiler, connection):
    """
    Return MQL for this KeyTransform (JSON path).

    JSON paths cannot always be represented simply as $var.key1.key2.key3 due
    to possible array types. Therefore, indexing arrays requires the use of
    `arrayElemAt`. Additionally, $cond is necessary to verify the type before
    performing the operation.
    """
    key_transforms = [self.key_name]
    previous = self.lhs
    while isinstance(previous, KeyTransform):
        key_transforms.insert(0, previous.key_name)
        previous = previous.lhs
    # Collect all key transforms in order.
    lhs_mql = previous.as_mql(compiler, connection, as_path=True)
    return build_json_mql_path(lhs_mql, key_transforms, as_path=True)


def key_transform_expr(self, compiler, connection):
    key_transforms = [self.key_name]
    previous = self.lhs
    while isinstance(previous, KeyTransform):
        key_transforms.insert(0, previous.key_name)
        previous = previous.lhs
    # Collect all key transforms in order.
    lhs_mql = previous.as_mql(compiler, connection, as_path=False)
    return build_json_mql_path(lhs_mql, key_transforms, as_path=False)


def key_transform_in(self, compiler, connection, as_path=False):
    """
    Return MQL to check if a JSON path exists and that its values are in the
    set of specified values (rhs).
    """
    if as_path and self.is_simple_expression():
        return builtin_lookup_path(self, compiler, connection)

    lhs_mql = process_lhs(self, compiler, connection)
    # Traverse to the root column.
    previous = self.lhs
    while isinstance(previous, KeyTransform):
        previous = previous.lhs
    root_column = previous.as_mql(compiler, connection)
    value = process_rhs(self, compiler, connection)
    # Construct the expression to check if lhs_mql values are in rhs values.
    expr = connection.mongo_operators_expr[self.lookup_name](lhs_mql, value)
    expr = {"$and": [_has_key_predicate(lhs_mql, root_column), expr]}
    if as_path:
        return {"$expr": expr}
    return expr


def key_transform_in_path(self, compiler, connection):
    return builtin_lookup_path(self, compiler, connection)


def key_transform_in_expr(self, compiler, connection):
    lhs_mql = process_lhs(self, compiler, connection)
    # Traverse to the root column.
    previous = self.lhs
    while isinstance(previous, KeyTransform):
        previous = previous.lhs
    root_column = previous.as_mql(compiler, connection)
    value = process_rhs(self, compiler, connection)
    # Construct the expression to check if lhs_mql values are in rhs values.
    expr = connection.mongo_operators_expr[self.lookup_name](lhs_mql, value)
    return {"$and": [_has_key_predicate(lhs_mql, root_column), expr]}


def key_transform_is_null_path(self, compiler, connection):
    """
    Return MQL to check the nullability of a key.

    If `isnull=True`, the query matches objects where the key is missing or the
    root column is null. If `isnull=False`, the query negates the result to
    match objects where the key exists.

    Reference: https://code.djangoproject.com/ticket/32252
    """
    lhs_mql = process_lhs(self, compiler, connection, as_path=True)
    rhs_mql = process_rhs(self, compiler, connection, as_path=True)
    return _has_key_predicate(lhs_mql, None, negated=rhs_mql, as_path=True)


def key_transform_is_null_expr(self, compiler, connection):
    previous = self.lhs
    while isinstance(previous, KeyTransform):
        previous = previous.lhs
    root_column = previous.as_mql(compiler, connection)
    lhs_mql = process_lhs(self, compiler, connection, as_path=False)
    rhs_mql = process_rhs(self, compiler, connection)
    return _has_key_predicate(lhs_mql, root_column, negated=rhs_mql)


def key_transform_numeric_lookup_mixin_path(self, compiler, connection):
    """
    Return MQL to check if the field exists (i.e., is not "missing" or "null")
    and that the field matches the given numeric lookup expression.
    """
    return builtin_lookup_path(self, compiler, connection)


def key_transform_numeric_lookup_mixin_expr(self, compiler, connection):
    """
    Return MQL to check if the field exists (i.e., is not "missing" or "null")
    and that the field matches the given numeric lookup expression.
    """
    lhs = process_lhs(self, compiler, connection, as_path=False)
    expr = builtin_lookup_expr(self, compiler, connection)
    # Check if the type of lhs is not "missing" or "null".
    not_missing_or_null = {"$not": {"$in": [{"$type": lhs}, ["missing", "null"]]}}
    return {"$and": [expr, not_missing_or_null]}


def key_transform_exact_path(self, compiler, connection):
    lhs_mql = process_lhs(self, compiler, connection, as_path=True)
    return {
        "$and": [
            builtin_lookup_path(self, compiler, connection),
            _has_key_predicate(lhs_mql, None, as_path=True),
        ]
    }


def key_transform_exact_expr(self, compiler, connection):
    return builtin_lookup_expr(self, compiler, connection)


def register_json_field():
    ContainedBy.as_mql = contained_by
    DataContains.as_mql = data_contains
    HasAnyKeys.mongo_operator = "$or"
    HasKey.mongo_operator = None
    # HasKeyLookup.as_mql = has_key_lookup
    HasKeyLookup.is_simple_expression = has_key_check_simple_expression
    HasKeyLookup.as_mql_path = has_key_lookup_path
    HasKeyLookup.as_mql_expr = has_key_lookup_expr
    HasKeys.mongo_operator = "$and"
    JSONExact.process_rhs = json_exact_process_rhs
    KeyTransform.is_simple_expression = is_simple_column
    # KeyTransform.as_mql = key_transform
    KeyTransform.as_mql_path = key_transform_path
    KeyTransform.as_mql_expr = key_transform_expr
    # KeyTransformIn.as_mql = key_transform_in
    KeyTransformIn.as_mql_path = key_transform_in_path
    KeyTransformIn.as_mql_expr = key_transform_in_expr
    # KeyTransformIsNull.as_mql = key_transform_is_null
    KeyTransformIsNull.as_mql_path = key_transform_is_null_path
    KeyTransformIsNull.as_mql_expr = key_transform_is_null_expr
    KeyTransformNumericLookupMixin.as_mql_path = key_transform_numeric_lookup_mixin_path
    KeyTransformNumericLookupMixin.as_mql_expr = key_transform_numeric_lookup_mixin_expr
    KeyTransformExact.as_mql_expr = key_transform_exact_expr
    KeyTransformExact.as_mql_path = key_transform_exact_path
