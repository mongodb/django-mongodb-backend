from django.db.models.aggregates import Aggregate, Count, StdDev, Variance
from django.db.models.expressions import Case, Value, When
from django.db.models.lookups import IsNull

from .query_utils import process_lhs

# Aggregates whose MongoDB aggregation name differ from Aggregate.function.lower().
MONGO_AGGREGATIONS = {Count: "sum"}


def aggregate(
    self,
    compiler,
    connection,
    operator=None,
    resolve_inner_expression=False,
    **extra_context,  # noqa: ARG001
):
    if self.filter:
        node = self.copy()
        node.filter = None
        source_expressions = node.get_source_expressions()
        condition = When(self.filter, then=source_expressions[0])
        node.set_source_expressions([Case(condition), *source_expressions[1:]])
    else:
        node = self
    lhs_mql = process_lhs(node, compiler, connection)
    if resolve_inner_expression:
        return lhs_mql
    operator = operator or MONGO_AGGREGATIONS.get(self.__class__, self.function.lower())
    return {f"${operator}": lhs_mql}


def count(self, compiler, connection, resolve_inner_expression=False, **extra_context):  # noqa: ARG001
    """
    When resolve_inner_expression=True, return the MQL that resolves as a
    value. This is used to count different elements, so the inner values are
    returned to be pushed into a set.
    """
    if not self.distinct or resolve_inner_expression:
        if self.filter:
            node = self.copy()
            node.filter = None
            source_expressions = node.get_source_expressions()
            condition = When(
                self.filter, then=Case(When(IsNull(source_expressions[0], False), then=Value(1)))
            )
            node.set_source_expressions([Case(condition), *source_expressions[1:]])
            inner_expression = process_lhs(node, compiler, connection)
        else:
            lhs_mql = process_lhs(self, compiler, connection)
            null_cond = {"$in": [{"$type": lhs_mql}, ["missing", "null"]]}
            inner_expression = {
                "$cond": {"if": null_cond, "then": None, "else": lhs_mql if self.distinct else 1}
            }
        if resolve_inner_expression:
            return inner_expression
        return {"$sum": inner_expression}
    # If distinct=True or resolve_inner_expression=False, sum the size of the
    # set.
    lhs_mql = process_lhs(self, compiler, connection)
    # None shouldn't be counted, so subtract 1 if it's present.
    exits_null = {"$cond": {"if": {"$in": [{"$literal": None}, lhs_mql]}, "then": -1, "else": 0}}
    return {"$add": [{"$size": lhs_mql}, exits_null]}


def stddev_variance(self, compiler, connection, **extra_context):
    if self.function.endswith("_SAMP"):
        operator = "stdDevSamp"
    elif self.function.endswith("_POP"):
        operator = "stdDevPop"
    return aggregate(self, compiler, connection, operator=operator, **extra_context)


def register_aggregates():
    Aggregate.as_mql = aggregate
    Count.as_mql = count
    StdDev.as_mql = stddev_variance
    Variance.as_mql = stddev_variance
