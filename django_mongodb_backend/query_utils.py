from django.core.exceptions import EmptyResultSet, FullResultSet
from django.db.models import F
from django.db.models.expressions import CombinedExpression, Func, Value
from django.db.models.sql.query import Query


def is_direct_value(node):
    return not hasattr(node, "as_sql")


def process_lhs(node, compiler, connection, as_expr=False):
    if not hasattr(node, "lhs"):
        # node is a Func or Expression, possibly with multiple source expressions.
        result = []
        for expr in node.get_source_expressions():
            if expr is None:
                continue
            try:
                result.append(expr.as_mql(compiler, connection, as_expr=as_expr))
            except FullResultSet:
                result.append(Value(True).as_mql(compiler, connection, as_expr=as_expr))
            except EmptyResultSet:
                result.append(Value(None).as_mql(compiler, connection, as_expr=as_expr))
        return result
    # node is a Transform with just one source expression, aliased as "lhs".
    if is_direct_value(node.lhs):
        return node
    return node.lhs.as_mql(compiler, connection, as_expr=as_expr)


def process_rhs(node, compiler, connection, as_expr=False):
    rhs = node.rhs
    if hasattr(rhs, "as_mql"):
        if getattr(rhs, "subquery", False) and hasattr(node, "get_subquery_wrapping_pipeline"):
            value = rhs.as_mql(
                compiler,
                connection,
                get_wrapping_pipeline=node.get_subquery_wrapping_pipeline,
                as_expr=as_expr,
            )
        else:
            value = rhs.as_mql(compiler, connection, as_expr=as_expr)
    else:
        _, value = node.process_rhs(compiler, connection)
        lookup_name = node.lookup_name
        # Undo Lookup.get_db_prep_lookup() putting params in a list.
        if lookup_name not in ("in", "range"):
            value = value[0]
    if hasattr(node, "prep_lookup_value_mongo"):
        value = node.prep_lookup_value_mongo(value)
    return value


def is_constant_value(value):
    if isinstance(value, CombinedExpression):
        # Treat all CombinedExpressions as non-constant until constant cases
        # are handled: https://jira.mongodb.org/browse/INTPYTHON-783.
        return False
    if isinstance(value, list):
        return all(map(is_constant_value, value))
    if is_direct_value(value):
        return True
    if hasattr(value, "get_source_expressions"):
        # Similar limitation as above, sub-expressions should be resolved in
        # the future.
        constants_sub_expressions = all(map(is_constant_value, value.get_source_expressions()))
    else:
        constants_sub_expressions = True
    constants_sub_expressions = constants_sub_expressions and not (
        isinstance(value, Query | F)
        or value.contains_aggregate
        or value.contains_over_clause
        or value.contains_column_references
        or value.contains_subquery
    )
    return constants_sub_expressions and (
        isinstance(value, Value)
        or
        # Some closed functions cannot yet be converted to constant values.
        # Allow Func with can_use_path as a temporary exception.
        (isinstance(value, Func) and value.can_use_path)
    )
