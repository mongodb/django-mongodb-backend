from django.db.models.expressions import Expression, Func
from django.db.models.fields import TextField


class NullSafeArraySum(Func):
    """
    Compute the sum of an array column, returning None if the array is empty.
    Used as the project-stage replacement for Sum to match SQL SUM() semantics
    (NULL for no rows, rather than MongoDB's $sum returning 0).
    """

    def as_mql(self, compiler, connection, as_expr=False):
        col_expr = self.source_expressions[0]
        # When a collection is empty, the wrapping stage injects an empty
        # document to support default= on aggregates — that document has no
        # array field at all, so $size gets missing type. $ifNull guards
        # against that.
        array_mql = {"$ifNull": [col_expr.as_mql(compiler, connection, as_expr=True), []]}
        mql = {
            "$cond": [
                {"$eq": [{"$size": array_mql}, 0]},
                None,
                {"$sum": array_mql},
            ]
        }
        return mql if as_expr else {"$expr": mql}


class Remove(Func):
    def as_mql(self, compiler, connection, as_expr=False):
        return "$$REMOVE"


class StringAggJoin(Expression):
    """
    Post-group expression that joins a $push'd or $addToSet'd array with a
    delimiter using $reduce/$concat. Return null for empty arrays, consistent
    with SQL STRING_AGG behavior.

    When sort_spec is provided (list of (field_name, direction) tuples), the
    pushed array contains {v: value, k0: key, ...} objects. This class then
    sorts by the key fields and extracts the values before joining.

    When scalar_sort is provided (1 or -1), the array contains plain scalar
    values (from $addToSet for DISTINCT) and is sorted directly.
    """

    def __init__(self, array_expr, delimiter_wrapper, sort_spec=None, scalar_sort=None):
        super().__init__(output_field=TextField())
        self.array_expr = array_expr
        self.delimiter_wrapper = delimiter_wrapper
        self.sort_spec = sort_spec  # e.g. [("k0", 1), ("k1", -1)] or None
        self.scalar_sort = scalar_sort  # 1 or -1 for DISTINCT + ORDER BY, or None

    def get_source_expressions(self):
        return [self.array_expr, self.delimiter_wrapper]

    def set_source_expressions(self, exprs):
        self.array_expr, self.delimiter_wrapper = exprs

    def as_mql_expr(self, compiler, connection):
        array_mql = self.array_expr.as_mql(compiler, connection, as_expr=True)
        # StringAggDelimiter wraps the actual delimiter Value; unwrap it.
        delimiter_mql = self.delimiter_wrapper.get_source_expressions()[0].as_mql(
            compiler, connection, as_expr=True
        )
        if self.sort_spec:
            # Array contains {v: value, k0: key, ...} objects pushed by
            # string_agg().
            sorted_input = {
                "$sortArray": {
                    "input": {"$ifNull": [array_mql, []]},
                    "sortBy": dict(self.sort_spec),
                }
            }
            # Extract v values; rows excluded by a filter have no v field so
            # $$item.v is null — those are removed by the null check below.
            filtered = {
                "$filter": {
                    "input": {
                        "$map": {
                            "input": sorted_input,
                            "as": "item",
                            "in": "$$item.v",
                        }
                    },
                    "cond": {"$ne": ["$$this", None]},
                }
            }
        elif self.scalar_sort is not None:
            # Array contains plain scalar values from $addToSet (DISTINCT
            # case). Sort the values directly.
            filtered = {
                "$filter": {
                    "input": {
                        "$sortArray": {
                            "input": {"$ifNull": [array_mql, []]},
                            "sortBy": self.scalar_sort,
                        }
                    },
                    "cond": {"$ne": ["$$this", None]},
                }
            }
        else:
            # Guard against null (missing field from wrapping empty-result
            # pipelines), and filter out null values (SQL STRING_AGG ignores
            # nulls).
            filtered = {
                "$filter": {
                    "input": {"$ifNull": [array_mql, []]},
                    "cond": {"$ne": ["$$this", None]},
                }
            }
        return {
            "$let": {
                "vars": {"arr": filtered},
                "in": {
                    "$cond": [
                        {"$gt": [{"$size": "$$arr"}, 0]},
                        {
                            "$reduce": {
                                "input": {"$slice": ["$$arr", 1, {"$size": "$$arr"}]},
                                "initialValue": {"$arrayElemAt": ["$$arr", 0]},
                                "in": {"$concat": ["$$value", delimiter_mql, "$$this"]},
                            }
                        },
                        None,
                    ]
                },
            }
        }
