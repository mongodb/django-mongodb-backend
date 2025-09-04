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
    KeyTransformIn,
    KeyTransformIsNull,
    KeyTransformNumericLookupMixin,
)

from ..lookups import builtin_lookup
from ..query_utils import process_lhs, process_rhs


def build_json_mql_path(lhs, key_transforms):
    # Build the MQL path using the collected key transforms.
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


def contained_by(self, compiler, connection):  # noqa: ARG001
    raise NotSupportedError("contained_by lookup is not supported on this database backend.")


def data_contains(self, compiler, connection):  # noqa: ARG001
    raise NotSupportedError("contains lookup is not supported on this database backend.")


def _has_key_predicate(path, root_column, negated=False):
    """Return MQL to check for the existence of `path`."""
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


def has_key_lookup(self, compiler, connection):
    """Return MQL to check for the existence of a key."""
    rhs = self.rhs
    lhs = process_lhs(self, compiler, connection)
    if not isinstance(rhs, (list, tuple)):
        rhs = [rhs]
    paths = []
    # Transform any "raw" keys into KeyTransforms to allow consistent handling
    # in the code that follows.
    for key in rhs:
        rhs_json_path = key if isinstance(key, KeyTransform) else KeyTransform(key, self.lhs)
        paths.append(rhs_json_path.as_mql(compiler, connection))
    keys = []
    for path in paths:
        keys.append(_has_key_predicate(path, lhs))
    if self.mongo_operator is None:
        return keys[0]
    return {self.mongo_operator: keys}


_process_rhs = JSONExact.process_rhs


def json_exact_process_rhs(self, compiler, connection):
    """Skip JSONExact.process_rhs()'s conversion of None to "null"."""
    return (
        super(JSONExact, self).process_rhs(compiler, connection)
        if connection.vendor == "mongodb"
        else _process_rhs(self, compiler, connection)
    )


def key_transform(self, compiler, connection):
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
    lhs_mql = previous.as_mql(compiler, connection)
    return build_json_mql_path(lhs_mql, key_transforms)


def key_transform_in(self, compiler, connection):
    """
    Return MQL to check if a JSON path exists and that its values are in the
    set of specified values (rhs).
    """
    lhs_mql = process_lhs(self, compiler, connection)
    # Traverse to the root column.
    previous = self.lhs
    while isinstance(previous, KeyTransform):
        previous = previous.lhs
    root_column = previous.as_mql(compiler, connection)
    value = process_rhs(self, compiler, connection)
    # Construct the expression to check if lhs_mql values are in rhs values.
    expr = connection.mongo_operators[self.lookup_name](lhs_mql, value)
    return {"$and": [_has_key_predicate(lhs_mql, root_column), expr]}


def key_transform_is_null(self, compiler, connection):
    """
    Return MQL to check the nullability of a key.

    If `isnull=True`, the query matches objects where the key is missing or the
    root column is null. If `isnull=False`, the query negates the result to
    match objects where the key exists.

    Reference: https://code.djangoproject.com/ticket/32252
    """
    lhs_mql = process_lhs(self, compiler, connection)
    rhs_mql = process_rhs(self, compiler, connection)
    # Get the root column.
    previous = self.lhs
    while isinstance(previous, KeyTransform):
        previous = previous.lhs
    root_column = previous.as_mql(compiler, connection)
    return _has_key_predicate(lhs_mql, root_column, negated=rhs_mql)


def key_transform_numeric_lookup_mixin(self, compiler, connection):
    """
    Return MQL to check if the field exists (i.e., is not "missing" or "null")
    and that the field matches the given numeric lookup expression.
    """
    expr = builtin_lookup(self, compiler, connection)
    lhs = process_lhs(self, compiler, connection)
    # Check if the type of lhs is not "missing" or "null".
    not_missing_or_null = {"$not": {"$in": [{"$type": lhs}, ["missing", "null"]]}}
    return {"$and": [expr, not_missing_or_null]}


def register_json_field():
    ContainedBy.as_mql = contained_by
    DataContains.as_mql = data_contains
    HasAnyKeys.mongo_operator = "$or"
    HasKey.mongo_operator = None
    HasKeyLookup.as_mql = has_key_lookup
    HasKeys.mongo_operator = "$and"
    JSONExact.process_rhs = json_exact_process_rhs
    KeyTransform.as_mql = key_transform
    KeyTransformIn.as_mql = key_transform_in
    KeyTransformIsNull.as_mql = key_transform_is_null
    KeyTransformNumericLookupMixin.as_mql = key_transform_numeric_lookup_mixin
