import itertools
from collections import defaultdict

from django.core.checks import Error, Warning
from django.db import NotSupportedError
from django.db.models import DecimalField, FloatField, Index
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

    def check(self, model, connection):
        errors = []
        if not connection.features.supports_atlas_search:
            errors.append(
                Warning(
                    "This MongoDB server does not support atlas search.",
                    hint=(
                        "The index won't be created. Silence this warning if you "
                        "don't care about it."
                    ),
                    obj=self,
                    id=f"{self._error_id_prefix}.W001",
                )
            )
        return errors

    def search_index_data_types(self, field, db_type):
        """
        Map a model field's internal type to search index type.
        Reference: https://www.mongodb.com/docs/atlas/atlas-search/define-field-mappings/#data-types
        """
        if field.get_internal_type() == "UUIDField":
            return "uuid"
        if field.get_internal_type() in ("ObjectIdAutoField", "ObjectIdField"):
            return "ObjectId"
        if field.get_internal_type() == "EmbeddedModelField":
            return "embeddedDocuments"
        if db_type in ("int", "long"):
            return "number"
        if db_type == "binData":
            return "string"
        if db_type == "bool":
            return "boolean"
        if db_type == "object":
            return "document"
        return db_type

    def get_pymongo_index_model(
        self, model, schema_editor, field=None, unique=False, column_prefix=""
    ):
        if not schema_editor.connection.features.supports_atlas_search:
            return None
        fields = {}
        for field_name, _ in self.fields_orders:
            field_ = model._meta.get_field(field_name)
            type_ = self.search_index_data_types(field_, field_.db_type(schema_editor.connection))
            field_path = column_prefix + model._meta.get_field(field_name).column
            fields[field_path] = {"type": type_}
        return SearchIndexModel(
            definition={"mappings": {"dynamic": False, "fields": fields}}, name=self.name
        )


class VectorSearchIndex(SearchIndex):
    suffix = "vsi"
    ALLOWED_SIMILARITY_FUNCTIONS = frozenset(("euclidean", "cosine", "dotProduct"))
    _error_id_prefix = "django_mongodb_backend.indexes.VectorSearchIndex"

    def __init__(self, *expressions, similarities="cosine", **kwargs):
        super().__init__(*expressions, **kwargs)
        self.similarities = similarities
        for func in similarities if isinstance(similarities, list) else (similarities,):
            if func not in self.ALLOWED_SIMILARITY_FUNCTIONS:
                raise ValueError(
                    f"{func} isn't a valid similarity function, options "
                    f"are {', '.join(sorted(self.ALLOWED_SIMILARITY_FUNCTIONS))}"
                )

    def check(self, model, connection):
        errors = super().check(model, connection)
        viewed = set()
        expected_similarities = 0
        for field_name, _ in self.fields_orders:
            if field_name in viewed:
                errors.append(
                    Error(
                        f"Field '{field_name}' is defined more than once. Vector and filter "
                        "fields must use distinct field names.",
                        obj=self,
                        hint="If you need different configurations for the same field, "
                        "create separate indexes.",
                        id=f"{self._error_id_prefix}.E004",
                    )
                )
                continue
            viewed.add(field_name)
            field_ = model._meta.get_field(field_name)
            if isinstance(field_, ArrayField):
                expected_similarities += 1
                try:
                    int(field_.size)
                except (ValueError, TypeError):
                    errors.append(
                        Error(
                            f"Atlas vector search requires size on {field_name}.",
                            obj=self,
                            id=f"{self._error_id_prefix}.E001",
                        )
                    )
                if not isinstance(field_.base_field, FloatField | DecimalField):
                    errors.append(
                        Error(
                            "An Atlas vector search index requires the base "
                            "field of ArrayField Model.field_name "
                            "to be FloatField or DecimalField but "
                            f"is {field_.base_field.get_internal_type()}.",
                            obj=self,
                            id=f"{self._error_id_prefix}.E002",
                        )
                    )
            else:
                field_type = field_.db_type(connection)
                search_type = self.search_index_data_types(field_, field_type)
                # filter - for fields that contain boolean, date, objectId,
                # numeric, string, or UUID values. Reference:
                # https://www.mongodb.com/docs/atlas/atlas-vector-search/vector-search-type/#atlas-vector-search-index-fields
                if search_type not in {"number", "string", "boolean", "objectId", "uuid", "date"}:
                    errors.append(
                        Error(
                            f"Unsupported filter of type {field_.get_internal_type()}.",
                            obj=self,
                            id=f"{self._error_id_prefix}.E003",
                        )
                    )
        if isinstance(self.similarities, list) and expected_similarities != len(self.similarities):
            similarity_function_text = (
                "similarities functions" if expected_similarities != 1 else "similarity function"
            )
            errors.append(
                Error(
                    f"An Atlas vector search index requires the same number of similarities and "
                    f"vector fields, but {expected_similarities} "
                    f"{similarity_function_text} were expected and "
                    f"{len(self.similarities)} {'were' if len(self.similarities) != 1 else 'was'} "
                    "provided.",
                    obj=self,
                    id=f"{self._error_id_prefix}.E005",
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
            if isinstance(self.similarities, str)
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
