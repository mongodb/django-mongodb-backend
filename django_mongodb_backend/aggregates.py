from django.db.models.aggregates import (
    Aggregate,
    Count,
    StdDev,
    StringAgg,
    Sum,
    Variance,
)
from django.db.models.expressions import Case, OrderBy, Value, When
from django.db.models.functions.comparison import Coalesce
from django.db.models.lookups import IsNull
from django.db.models.sql.where import WhereNode

from django_mongodb_backend.expressions import Remove

# Aggregates whose MongoDB aggregation name differs from
# Aggregate.function.lower().
MONGO_AGGREGATIONS = {Count: "sum"}


def aggregate(self, compiler, connection, operator=None, resolve_inner_expression=False):
    agg_expression, *_ = self.get_source_expressions()
    if self.filter is not None:
        agg_expression = Case(
            When(self.filter.condition, then=agg_expression),
            # Skip rows that don't meet the criteria.
            default=Remove(),
        )
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
        conditions = [IsNull(agg_expression, False)]
        if self.filter:
            conditions.append(self.filter.condition)
        inner_expression = Case(
            When(WhereNode(conditions), then=agg_expression if self.distinct else Value(1)),
            # Skip rows that don't meet the criteria.
            default=Remove(),
        )
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


def string_agg(self, compiler, connection, resolve_inner_expression=False):
    agg_expression, *_ = self.get_source_expressions()
    if self.filter is not None:
        agg_expression = Case(
            When(self.filter.condition, then=agg_expression),
            default=Remove(),
        )
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


def sum_(self, compiler, connection, resolve_inner_expression=False):
    """
    Use $push (not $sum) in the group stage so that _get_replace_expr() can use
    NullSafeArraySum in the project stage, returning None instead of 0 when no
    rows contribute, matching SQL SUM() null semantics.

    A null check is added so that null values produce $$REMOVE, causing $push
    to skip them. This keeps the array empty when all values are null, letting
    NullSafeArraySum distinguish "no non-null values" (None) from "values
    summing to 0" (0).
    """
    agg_expression, *_ = self.get_source_expressions()
    # Always check for nulls; add the filter condition when present.
    conditions = [IsNull(agg_expression, False)]
    if self.filter:
        conditions.append(self.filter.condition)
    agg_expression = Case(
        When(WhereNode(conditions), then=agg_expression),
        default=Remove(),
    )
    lhs_mql = agg_expression.as_mql(compiler, connection, as_expr=True)
    if resolve_inner_expression:
        return lhs_mql
    return {"$push": lhs_mql}


def register_aggregates():
    Aggregate.as_mql_expr = aggregate
    Count.as_mql_expr = count
    StdDev.as_mql_expr = stddev_variance
    StringAgg.as_mql_expr = string_agg
    Sum.as_mql_expr = sum_
    Variance.as_mql_expr = stddev_variance
