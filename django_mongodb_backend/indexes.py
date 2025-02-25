from django.db import NotSupportedError
from django.db.models import Index
from django.db.models.lookups import BuiltinLookup
from django.db.models.sql.query import Query
from django.db.models.sql.where import AND, XOR, WhereNode
from pymongo import ASCENDING, DESCENDING
from pymongo.operations import IndexModel, SearchIndexModel

from .query_utils import process_rhs

MONGO_INDEX_OPERATORS = {
    "exact": "$eq",
    "gt": "$gt",
    "gte": "$gte",
    "lt": "$lt",
    "lte": "$lte",
    "in": "$in",
}


def _get_condition_mql(self, model, schema_editor):
    """Analogous to Index._get_condition_sql()."""
    query = Query(model=model, alias_cols=False)
    where = query.build_where(self.condition)
    compiler = query.get_compiler(connection=schema_editor.connection)
    return where.as_mql_idx(compiler, schema_editor.connection)


def builtin_lookup_idx(self, compiler, connection):
    lhs_mql = self.lhs.target.column
    value = process_rhs(self, compiler, connection)
    try:
        operator = MONGO_INDEX_OPERATORS[self.lookup_name]
    except KeyError:
        raise NotSupportedError(
            f"MongoDB does not support the '{self.lookup_name}' lookup in indexes."
        ) from None
    return {lhs_mql: {operator: value}}


def where_node_idx(self, compiler, connection):
    if self.connector == AND:
        operator = "$and"
    elif self.connector == XOR:
        raise NotSupportedError("MongoDB does not support the '^' operator lookup in indexes.")
    else:
        operator = "$or"
    if self.negated:
        raise NotSupportedError("MongoDB does not support the '~' operator in indexes.")
    children_mql = []
    for child in self.children:
        mql = child.as_mql_idx(compiler, connection)
        children_mql.append(mql)
    if len(children_mql) == 1:
        mql = children_mql[0]
    elif len(children_mql) > 1:
        mql = {operator: children_mql}
    else:
        mql = {}
    return mql


def create_mongodb_index(
    self,
    model,
    schema_editor,
    *,
    connection=None,  # noqa: ARG001
    field=None,
    unique=False,
    column_prefix="",
):
    from collections import defaultdict

    if self.contains_expressions:
        return None
    kwargs = {}
    filter_expression = defaultdict(dict)
    if self.condition:
        filter_expression.update(self._get_condition_mql(model, schema_editor))
    if unique:
        kwargs["unique"] = True
        # Indexing on $type matches the value of most SQL databases by
        # allowing multiple null values for the unique constraint.
        if field:
            column = column_prefix + field.column
            filter_expression[column].update({"$type": field.db_type(schema_editor.connection)})
        else:
            for field_name, _ in self.fields_orders:
                field_ = model._meta.get_field(field_name)
                filter_expression[field_.column].update(
                    {"$type": field_.db_type(schema_editor.connection)}
                )
    if filter_expression:
        kwargs["partialFilterExpression"] = filter_expression
    index_orders = (
        [(column_prefix + field.column, ASCENDING)]
        if field
        else [
            # order is "" if ASCENDING or "DESC" if DESCENDING (see
            # django.db.models.indexes.Index.fields_orders).
            (
                column_prefix + model._meta.get_field(field_name).column,
                ASCENDING if order == "" else DESCENDING,
            )
            for field_name, order in self.fields_orders
        ]
    )
    return IndexModel(index_orders, name=self.name, **kwargs)


class AtlasSearchIndex(Index):
    suffix = "atlas_search"

    def __init__(self, *expressions, **kwargs):
        super().__init__(*expressions, **kwargs)

    def create_mongodb_index(
        self, model, schema_editor, connection=None, field=None, unique=False, column_prefix=""
    ):
        fields = {}
        for field_name, _ in self.fields_orders:
            field_ = model._meta.get_field(field_name)
            type_ = connection.mongo_data_types[field_.get_internal_type()]
            fields[field_name] = {"type": type_}
        return SearchIndexModel(
            definition={"mappings": {"dynamic": False, "fields": fields}}, name=self.name
        )


def register_indexes():
    BuiltinLookup.as_mql_idx = builtin_lookup_idx
    Index._get_condition_mql = _get_condition_mql
    Index.create_mongodb_index = create_mongodb_index
    WhereNode.as_mql_idx = where_node_idx
