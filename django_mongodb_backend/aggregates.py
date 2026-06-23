from django.db import NotSupportedError
from django.db.models.aggregates import (
    Aggregate,
    Count,
    StdDev,
    StringAgg,
    Variance,
)
from django.db.models.expressions import Case, Expression, OrderBy, Value, When
from django.db.models.fields import TextField
from django.db.models.functions.comparison import Coalesce
from django.db.models.lookups import IsNull
from django.db.models.sql.where import WhereNode

from django_mongodb_backend.expressions import Remove

# Aggregates whose MongoDB aggregation name differs from
# Aggregate.function.lower().
MONGO_AGGREGATIONS = {Count: "sum"}


def aggregate(self, compiler, connection, operator=None, resolve_inner_expression=False):
    agg_expression, *_ = self.get_source_expressions()
    lhs_mql = None
    if self.filter is not None:
        try:
            lhs_mql = self.filter.as_mql(compiler, connection, as_expr=True)
        except NotSupportedError:
            # Generate a CASE statement for this AggregateFilter.
            agg_expression = Case(
                When(self.filter.condition, then=agg_expression),
                # Skip rows that don't meet the criteria.
                default=Remove(),
            )
    if lhs_mql is None:
        lhs_mql = agg_expression.as_mql(compiler, connection, as_expr=True)
    if resolve_inner_expression:
        return lhs_mql
    operator = operator or MONGO_AGGREGATIONS.get(self.__class__, self.function.lower())
    return {f"${operator}": lhs_mql}


def count(self, compiler, connection, resolve_inner_expression=False):
    """
    When resolve_inner_expression=True, return the MQL that resolves as a
    value. This is used to count different elements, so the inner values are
    returned to be pushed into a set.
    """
    agg_expression, *_ = self.get_source_expressions()
    if not self.distinct or resolve_inner_expression:
        lhs_mql = None
        conditions = [IsNull(agg_expression, False)]
        if self.filter:
            try:
                lhs_mql = self.filter.as_mql(compiler, connection, as_expr=True)
            except NotSupportedError:
                # Generate a CASE statement for this AggregateFilter.
                conditions.append(self.filter.condition)
                condition = When(
                    WhereNode(conditions),
                    then=agg_expression if self.distinct else Value(1),
                )
                inner_expression = Case(condition, default=Remove())
        else:
            inner_expression = Case(
                When(WhereNode(conditions), then=agg_expression if self.distinct else Value(1)),
                # Skip rows that don't meet the criteria.
                default=Remove(),
            )
        if lhs_mql is None:
            lhs_mql = inner_expression.as_mql(compiler, connection, as_expr=True)
        if resolve_inner_expression:
            return lhs_mql
        return {"$sum": lhs_mql}
    # Normalize empty documents (introduced by aggregation wrapping) to an
    # empty set fallback.
    agg_expression = Coalesce(agg_expression, [])
    # If distinct=True or resolve_inner_expression=False, sum the size of the
    # set.
    return {"$size": agg_expression.as_mql(compiler, connection, as_expr=True)}


def stddev_variance(self, compiler, connection):
    if self.function.endswith("_SAMP"):
        operator = "stdDevSamp"
    elif self.function.endswith("_POP"):
        operator = "stdDevPop"
    return aggregate(self, compiler, connection, operator=operator)


class StringAggJoin(Expression):
    """
    Post-group expression that joins a $push'd or $addToSet'd array with a
    delimiter using $reduce/$concat. Return null for empty arrays, consistent
    with SQL STRING_AGG behavior.

    When sort_spec is provided (list of (field_name, direction) tuples), the
    pushed array contains {v: value, k0: key, ...} objects. This class then
    sorts by the key fields and extracts the values before joining.
    """

    def __init__(self, array_expr, delimiter_wrapper, sort_spec=None):
        super().__init__(output_field=TextField())
        self.array_expr = array_expr
        self.delimiter_wrapper = delimiter_wrapper
        self.sort_spec = sort_spec  # e.g. [("k0", 1), ("k1", -1)] or None

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
                                "input": "$$arr",
                                "initialValue": "",
                                "in": {
                                    "$concat": [
                                        "$$value",
                                        {
                                            "$cond": [
                                                {"$eq": ["$$value", ""]},
                                                "",
                                                delimiter_mql,
                                            ]
                                        },
                                        "$$this",
                                    ]
                                },
                            }
                        },
                        None,
                    ]
                },
            }
        }


def string_agg(self, compiler, connection, resolve_inner_expression=False):
    agg_expression, *_ = self.get_source_expressions()
    lhs_mql = None
    if self.filter is not None:
        try:
            lhs_mql = self.filter.as_mql(compiler, connection, as_expr=True)
        except NotSupportedError:
            agg_expression = Case(
                When(self.filter.condition, then=agg_expression),
                default=Remove(),
            )
    if lhs_mql is None:
        lhs_mql = agg_expression.as_mql(compiler, connection, as_expr=True)
    if resolve_inner_expression:
        return lhs_mql
    if self.order_by:
        # Push {v: value, k0: sort_key, ...} so StringAggJoin can sort the
        # array in the post-group stage using $sortArray.
        sort_keys = {}
        for i, expr in enumerate(self.order_by.get_source_expressions()):
            key_expr = expr.expression if isinstance(expr, OrderBy) else expr
            sort_keys[f"k{i}"] = key_expr.as_mql(compiler, connection, as_expr=True)
        return {"$push": {"v": lhs_mql, **sort_keys}}
    return {"$push": lhs_mql}


def register_aggregates():
    Aggregate.as_mql_expr = aggregate
    Count.as_mql_expr = count
    StdDev.as_mql_expr = stddev_variance
    StringAgg.as_mql_expr = string_agg
    Variance.as_mql_expr = stddev_variance
