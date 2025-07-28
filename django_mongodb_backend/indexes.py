import itertools
from collections import defaultdict

from django.core.checks import Error, Warning
from django.db import NotSupportedError
from django.db.models import FloatField, Index, IntegerField
from django.db.models.lookups import BuiltinLookup
from django.db.models.sql.query import Query
from django.db.models.sql.where import AND, XOR, WhereNode
from pymongo import ASCENDING, DESCENDING
from pymongo.operations import IndexModel, SearchIndexModel

from django_mongodb_backend.fields import ArrayField

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


def get_pymongo_index_model(self, model, schema_editor, field=None, unique=False, column_prefix=""):
    """Return a pymongo IndexModel for this Django Index."""
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


class SearchIndex(Index):
    suffix = "six"
    _error_id_prefix = "django_mongodb_backend.indexes.SearchIndex"

    def __init__(self, *, fields=(), name=None):
        super().__init__(fields=fields, name=name)

    def check(self, model, connection):
        errors = []
        if not connection.features.supports_atlas_search:
            errors.append(
                Warning(
                    f"This MongoDB server does not support {self.__class__.__name__}.",
                    hint=(
                        "The index won't be created. Use an Atlas-enabled version of MongoDB, "
                        "or silence this warning if you don't care about it."
                    ),
                    obj=model,
                    id=f"{self._error_id_prefix}.W001",
                )
            )
        return errors

    def search_index_data_types(self, db_type):
        """
        Map a model field's type to search index type.
        https://www.mongodb.com/docs/atlas/atlas-search/define-field-mappings/#data-types
        """
        if db_type in {"double", "int", "long"}:
            return "number"
        if db_type == "binData":
            return "string"
        if db_type == "bool":
            return "boolean"
        if db_type == "object":
            return "document"
        if db_type == "array":
            return "embeddedDocuments"
        return db_type

    def get_pymongo_index_model(
        self, model, schema_editor, field=None, unique=False, column_prefix=""
    ):
        if not schema_editor.connection.features.supports_atlas_search:
            return None
        fields = {}
        for field_name, _ in self.fields_orders:
            field = model._meta.get_field(field_name)
            type_ = self.search_index_data_types(field.db_type(schema_editor.connection))
            field_path = column_prefix + model._meta.get_field(field_name).column
            fields[field_path] = {"type": type_}
        return SearchIndexModel(
            definition={"mappings": {"dynamic": False, "fields": fields}}, name=self.name
        )


class VectorSearchIndex(SearchIndex):
    suffix = "vsi"
    _error_id_prefix = "django_mongodb_backend.indexes.VectorSearchIndex"
    VALID_FIELD_TYPES = frozenset(("boolean", "date", "number", "objectId", "string", "uuid"))
    VALID_SIMILARITIES = frozenset(("cosine", "dotProduct", "euclidean"))

    def __init__(self, *, fields=(), name=None, similarities):
        super().__init__(fields=fields, name=name)
        self.similarities = similarities
        self._multiple_similarities = isinstance(similarities, tuple | list)
        for func in similarities if self._multiple_similarities else (similarities,):
            if func not in self.VALID_SIMILARITIES:
                raise ValueError(
                    f"'{func}' isn't a valid similarity function "
                    f"({', '.join(sorted(self.VALID_SIMILARITIES))})."
                )
        seen_fields = set()
        for field_name, _ in self.fields_orders:
            if field_name in seen_fields:
                raise ValueError(f"Field '{field_name}' is duplicated in fields.")
            seen_fields.add(field_name)

    def check(self, model, connection):
        errors = super().check(model, connection)
        num_arrayfields = 0
        for field_name, _ in self.fields_orders:
            field = model._meta.get_field(field_name)
            if isinstance(field, ArrayField):
                num_arrayfields += 1
                try:
                    int(field.size)
                except (ValueError, TypeError):
                    errors.append(
                        Error(
                            f"VectorSearchIndex requires 'size' on field '{field_name}'.",
                            obj=model,
                            id=f"{self._error_id_prefix}.E002",
                        )
                    )
                if not isinstance(field.base_field, FloatField | IntegerField):
                    errors.append(
                        Error(
                            "VectorSearchIndex requires the base field of "
                            f"ArrayField '{field.name}' to be FloatField or "
                            "IntegerField but is "
                            f"{field.base_field.get_internal_type()}.",
                            obj=model,
                            id=f"{self._error_id_prefix}.E003",
                        )
                    )
            else:
                search_type = self.search_index_data_types(field.db_type(connection))
                if search_type not in self.VALID_FIELD_TYPES:
                    errors.append(
                        Error(
                            "VectorSearchIndex does not support field "
                            f"'{field_name}' ({field.get_internal_type()}).",
                            obj=model,
                            id=f"{self._error_id_prefix}.E004",
                            hint=f"Allowed types are {', '.join(sorted(self.VALID_FIELD_TYPES))}.",
                        )
                    )
        if self._multiple_similarities and num_arrayfields != len(self.similarities):
            errors.append(
                Error(
                    f"VectorSearchIndex requires the same number of similarities "
                    f"and vector fields; {model._meta.object_name} has "
                    f"{num_arrayfields} ArrayField(s) but similarities "
                    f"has {len(self.similarities)} element(s).",
                    obj=model,
                    id=f"{self._error_id_prefix}.E005",
                )
            )
        if num_arrayfields == 0:
            errors.append(
                Error(
                    "VectorSearchIndex requires at least one ArrayField to store vector data.",
                    obj=model,
                    id=f"{self._error_id_prefix}.E006",
                    hint="If you want to perform search operations without vectors, "
                    "use SearchIndex instead.",
                )
            )
        return errors

    def deconstruct(self):
        path, args, kwargs = super().deconstruct()
        kwargs["similarities"] = self.similarities
        return path, args, kwargs

    def get_pymongo_index_model(
        self, model, schema_editor, field=None, unique=False, column_prefix=""
    ):
        if not schema_editor.connection.features.supports_atlas_search:
            return None
        similarities = (
            itertools.cycle([self.similarities])
            if not self._multiple_similarities
            else iter(self.similarities)
        )
        fields = []
        for field_name, _ in self.fields_orders:
            field_ = model._meta.get_field(field_name)
            field_path = column_prefix + model._meta.get_field(field_name).column
            mappings = {"path": field_path}
            if isinstance(field_, ArrayField):
                mappings.update(
                    {
                        "type": "vector",
                        "numDimensions": int(field_.size),
                        "similarity": next(similarities),
                    }
                )
            else:
                mappings["type"] = "filter"
            fields.append(mappings)
        return SearchIndexModel(definition={"fields": fields}, name=self.name, type="vectorSearch")


def register_indexes():
    BuiltinLookup.as_mql_idx = builtin_lookup_idx
    Index._get_condition_mql = _get_condition_mql
    Index.get_pymongo_index_model = get_pymongo_index_model
    WhereNode.as_mql_idx = where_node_idx
