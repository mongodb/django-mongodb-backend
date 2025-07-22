import datetime
from decimal import Decimal
from uuid import UUID

from bson import Decimal128
from django.core.exceptions import EmptyResultSet, FullResultSet
from django.db import NotSupportedError
from django.db.models.expressions import (
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

from ..query_utils import process_lhs


def case(self, compiler, connection):
    case_parts = []
    for case in self.cases:
        case_mql = {}
        try:
            case_mql["case"] = case.as_mql(compiler, connection)
        except EmptyResultSet:
            continue
        except FullResultSet:
            default_mql = case.result.as_mql(compiler, connection)
            break
        case_mql["then"] = case.result.as_mql(compiler, connection)
        case_parts.append(case_mql)
    else:
        default_mql = self.default.as_mql(compiler, connection)
    if not case_parts:
        return default_mql
    return {
        "$switch": {
            "branches": case_parts,
            "default": default_mql,
        }
    }


def col(self, compiler, connection, as_path=False):  # noqa: ARG001
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
    if not as_path:
        prefix = f"${prefix}"
    return f"{prefix}{self.target.column}"


def col_pairs(self, compiler, connection):
    cols = self.get_cols()
    if len(cols) > 1:
        raise NotSupportedError("ColPairs is not supported.")
    return cols[0].as_mql(compiler, connection)


def combined_expression(self, compiler, connection):
    expressions = [
        self.lhs.as_mql(compiler, connection),
        self.rhs.as_mql(compiler, connection),
    ]
    return connection.ops.combine_expression(self.connector, expressions)


def expression_wrapper(self, compiler, connection):
    return self.expression.as_mql(compiler, connection)


def negated_expression(self, compiler, connection):
    return {"$not": expression_wrapper(self, compiler, connection)}


def order_by(self, compiler, connection):
    return self.expression.as_mql(compiler, connection)


def query(self, compiler, connection, get_wrapping_pipeline=None):
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
            compiler.PARENT_FIELD_TEMPLATE.format(i): col.as_mql(compiler, connection)
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
    return f"${table_output}.{field_name}"


def raw_sql(self, compiler, connection):  # noqa: ARG001
    raise NotSupportedError("RawSQL is not supported on MongoDB.")


def ref(self, compiler, connection):  # noqa: ARG001
    prefix = (
        f"{self.source.alias}."
        if isinstance(self.source, Col) and self.source.alias != compiler.collection_name
        else ""
    )
    if hasattr(self, "ordinal"):
        refs, _ = compiler.columns[self.ordinal - 1]
    else:
        refs = self.refs
    return f"${prefix}{refs}"


def star(self, compiler, connection):  # noqa: ARG001
    return {"$literal": True}


def subquery(self, compiler, connection, get_wrapping_pipeline=None):
    return self.query.as_mql(compiler, connection, get_wrapping_pipeline=get_wrapping_pipeline)


def exists(self, compiler, connection, get_wrapping_pipeline=None):
    try:
        lhs_mql = subquery(self, compiler, connection, get_wrapping_pipeline=get_wrapping_pipeline)
    except EmptyResultSet:
        return Value(False).as_mql(compiler, connection)
    return connection.mongo_operators["isnull"](lhs_mql, False)


def when(self, compiler, connection):
    return self.condition.as_mql(compiler, connection)


def value(self, compiler, connection):  # noqa: ARG001
    value = self.value
    if isinstance(value, list | int):
        # Wrap lists & numbers in $literal to prevent ambiguity when Value
        # appears in $project.
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
    Case.as_mql = case
    Col.as_mql = col
    ColPairs.as_mql = col_pairs
    CombinedExpression.as_mql = combined_expression
    Exists.as_mql = exists
    ExpressionList.as_mql = process_lhs
    ExpressionWrapper.as_mql = expression_wrapper
    NegatedExpression.as_mql = negated_expression
    OrderBy.as_mql = order_by
    Query.as_mql = query
    RawSQL.as_mql = raw_sql
    Ref.as_mql = ref
    ResolvedOuterRef.as_mql = ResolvedOuterRef.as_sql
    Star.as_mql = star
    Subquery.as_mql = subquery
    When.as_mql = when
    Value.as_mql = value
