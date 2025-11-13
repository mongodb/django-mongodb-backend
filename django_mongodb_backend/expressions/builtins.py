import datetime
from decimal import Decimal
from functools import partialmethod
from uuid import UUID

from bson import Decimal128
from django.core.exceptions import EmptyResultSet, FullResultSet
from django.db import NotSupportedError
from django.db.models.expressions import (
    BaseExpression,
    Case,
    Col,
    ColPairs,
    CombinedExpression,
    Exists,
    ExpressionList,
    ExpressionWrapper,
    NegatedExpression,
    OrderBy,
    RawSQL,
    Ref,
    ResolvedOuterRef,
    Star,
    Subquery,
    Value,
    When,
)
from django.db.models.sql import Query

from django_mongodb_backend.query_utils import process_lhs


def base_expression(self, compiler, connection, as_expr=False, **extra):
    # Use as_mql_path(), if possible.
    if not as_expr and hasattr(self, "as_mql_path") and getattr(self, "can_use_path", False):
        return self.as_mql_path(compiler, connection, **extra)
    # Otherwise, use as_mql_expr().
    expr = self.as_mql_expr(compiler, connection, **extra)
    return expr if as_expr else {"$expr": expr}


def case(self, compiler, connection):
    case_parts = []
    for case in self.cases:
        case_mql = {}
        try:
            case_mql["case"] = case.as_mql(compiler, connection, as_expr=True)
        except EmptyResultSet:
            continue
        except FullResultSet:
            default_mql = case.result.as_mql(compiler, connection, as_expr=True)
            break
        case_mql["then"] = case.result.as_mql(compiler, connection, as_expr=True)
        case_parts.append(case_mql)
    else:
        default_mql = self.default.as_mql(compiler, connection, as_expr=True)
    if not case_parts:
        return default_mql
    return {
        "$switch": {
            "branches": case_parts,
            "default": default_mql,
        }
    }


def col(self, compiler, connection, as_expr=False):  # noqa: ARG001
    # If the column is part of a subquery and belongs to one of the parent
    # queries, it will be stored for reference using $let in a $lookup stage.
    # If the query is built with `alias_cols=False`, treat the column as
    # belonging to the current collection.
    if self.alias is not None and (
        self.alias not in compiler.query.alias_refcount
        or compiler.query.alias_refcount[self.alias] == 0
    ):
        try:
            index = compiler.column_indices[self]
        except KeyError:
            index = len(compiler.column_indices)
            compiler.column_indices[self] = index
        return f"$${compiler.PARENT_FIELD_TEMPLATE.format(index)}"
    # Add the column's collection's alias for columns in joined collections.
    has_alias = self.alias and self.alias != compiler.collection_name
    prefix = f"{self.alias}." if has_alias else ""
    if as_expr:
        prefix = f"${prefix}"
    return f"{prefix}{self.target.column}"


def col_pairs(self, compiler, connection, as_expr=False):
    cols = self.get_cols()
    if len(cols) > 1:
        raise NotSupportedError("ColPairs is not supported.")
    return cols[0].as_mql(compiler, connection, as_expr=as_expr)


def combined_expression(self, compiler, connection):
    expressions = [
        self.lhs.as_mql(compiler, connection, as_expr=True),
        self.rhs.as_mql(compiler, connection, as_expr=True),
    ]
    return connection.ops.combine_expression(self.connector, expressions)


def expression_wrapper(self, compiler, connection):
    return self.expression.as_mql(compiler, connection, as_expr=True)


def negated_expression(self, compiler, connection):
    return {"$not": expression_wrapper(self, compiler, connection)}


def order_by(self, compiler, connection, as_expr=False):
    return self.expression.as_mql(compiler, connection, as_expr=as_expr)


@property
def order_by_can_use_path(self):
    return self.expression.is_simple_column


def query(self, compiler, connection, get_wrapping_pipeline=None, as_expr=False):
    subquery_compiler = self.get_compiler(connection=connection)
    subquery_compiler.pre_sql_setup(with_col_aliases=False)
    field_name, expr = subquery_compiler.columns[0]
    subquery = subquery_compiler.build_query(
        subquery_compiler.columns
        if subquery_compiler.query.annotations or not subquery_compiler.query.default_cols
        else None
    )
    table_output = f"__subquery{len(compiler.subqueries)}"
    from_table = next(
        e.table_name for alias, e in self.alias_map.items() if self.alias_refcount[alias]
    )
    # To perform a subquery, a $lookup stage that escapsulates the entire
    # subquery pipeline is added. The "let" clause defines the variables
    # needed to bridge the main collection with the subquery.
    subquery.subquery_lookup = {
        "as": table_output,
        "from": from_table,
        "let": {
            compiler.PARENT_FIELD_TEMPLATE.format(i): col.as_mql(compiler, connection, as_expr=True)
            for col, i in subquery_compiler.column_indices.items()
        },
    }
    if get_wrapping_pipeline:
        # The results from some lookups must be converted to a list of values.
        # The output is compressed with an aggregation pipeline.
        wrapping_result_pipeline = get_wrapping_pipeline(
            subquery_compiler, connection, field_name, expr
        )
        # If the subquery is a combinator, wrap the result at the end of the
        # combinator pipeline...
        if subquery.query.combinator:
            subquery.combinator_pipeline.extend(wrapping_result_pipeline)
        # ... otherwise put at the end of subquery's pipeline.
        else:
            if subquery.aggregation_pipeline is None:
                subquery.aggregation_pipeline = []
            subquery.aggregation_pipeline.extend(wrapping_result_pipeline)
        # Erase project_fields since the required value is projected above.
        subquery.project_fields = None
    compiler.subqueries.append(subquery)
    if as_expr:
        return f"${table_output}.{field_name}"
    return f"{table_output}.{field_name}"


def raw_sql(self, compiler, connection, as_expr=False):  # noqa: ARG001
    raise NotSupportedError("RawSQL is not supported on MongoDB.")


def ref(self, compiler, connection, as_expr=False):  # noqa: ARG001
    prefix = (
        f"{self.source.alias}."
        if isinstance(self.source, Col) and self.source.alias != compiler.collection_name
        else ""
    )
    if hasattr(self, "ordinal"):
        refs, _ = compiler.columns[self.ordinal - 1]
    else:
        refs = self.refs
    if as_expr:
        prefix = f"${prefix}"
    return f"{prefix}{refs}"


def star(self, compiler, connection):  # noqa: ARG001
    return {"$literal": True}


def subquery(self, compiler, connection, get_wrapping_pipeline=None, as_expr=False):
    return self.query.as_mql(
        compiler, connection, get_wrapping_pipeline=get_wrapping_pipeline, as_expr=as_expr
    )


def exists(self, compiler, connection, get_wrapping_pipeline=None):
    try:
        lhs_mql = subquery(
            self, compiler, connection, get_wrapping_pipeline=get_wrapping_pipeline, as_expr=True
        )
    except EmptyResultSet:
        return Value(False).as_mql(compiler, connection, as_expr=True)
    return connection.mongo_expr_operators["isnull"](lhs_mql, False)


def when(self, compiler, connection):
    return self.condition.as_mql(compiler, connection, as_expr=True)


def value(self, compiler, connection, as_expr=False):  # noqa: ARG001
    value = self.value
    if isinstance(value, (list, int, str, dict, tuple)) and as_expr:
        # Wrap lists, numbers, strings, dicts, and tuples in $literal to avoid
        # ambiguity when Value is used in aggregate() or update_many()'s $set.
        return {"$literal": value}
    if isinstance(value, Decimal):
        return Decimal128(value)
    if isinstance(value, datetime.datetime):
        return value
    if isinstance(value, datetime.date):
        # Turn dates into datetimes since BSON doesn't support dates.
        return datetime.datetime.combine(value, datetime.datetime.min.time())
    if isinstance(value, datetime.time):
        # Turn times into datetimes since BSON doesn't support times.
        return datetime.datetime.combine(datetime.datetime.min.date(), value)
    if isinstance(value, datetime.timedelta):
        # DurationField stores milliseconds rather than microseconds.
        return value / datetime.timedelta(milliseconds=1)
    if isinstance(value, UUID):
        return value.hex
    return value


def register_expressions():
    BaseExpression.as_mql = base_expression
    BaseExpression.is_simple_column = False
    Case.as_mql_expr = case
    Col.as_mql = col
    Col.is_simple_column = True
    ColPairs.as_mql = col_pairs
    CombinedExpression.as_mql_expr = combined_expression
    Exists.as_mql_expr = exists
    ExpressionList.as_mql = process_lhs
    ExpressionWrapper.as_mql_expr = expression_wrapper
    NegatedExpression.as_mql_expr = negated_expression
    OrderBy.as_mql_expr = partialmethod(order_by, as_expr=True)
    OrderBy.as_mql_path = partialmethod(order_by, as_expr=False)
    OrderBy.can_use_path = order_by_can_use_path
    Query.as_mql = query
    RawSQL.as_mql = raw_sql
    Ref.as_mql = ref
    Ref.is_simple_column = True
    ResolvedOuterRef.as_mql = ResolvedOuterRef.as_sql
    Star.as_mql_expr = star
    Subquery.as_mql_expr = partialmethod(subquery, as_expr=True)
    Subquery.as_mql_path = partialmethod(subquery, as_expr=False)
    When.as_mql_expr = when
    Value.as_mql = value
