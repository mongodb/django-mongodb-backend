from django.db import NotSupportedError
from django.db.models.aggregates import (
    Aggregate,
    Count,
    StdDev,
    StringAgg,
    Variance,
)
from django.db.models.expressions import Case, Value, When
from django.db.models.functions.comparison import Coalesce
from django.db.models.lookups import IsNull
from django.db.models.sql.where import WhereNode

from django_mongodb_backend.expressions import Remove

# Aggregates whose MongoDB aggregation name differ from Aggregate.function.lower().
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


def string_agg(self, compiler, connection):  # noqa: ARG001
    raise NotSupportedError("StringAgg is not supported.")


def register_aggregates():
    Aggregate.as_mql_expr = aggregate
    Count.as_mql_expr = count
    StdDev.as_mql_expr = stddev_variance
    StringAgg.as_mql_expr = string_agg
    Variance.as_mql_expr = stddev_variance
