from unittest import mock

from django.db import connection
from django.test import SimpleTestCase, TestCase, skipUnlessDBFeature

from django_mongodb_backend.indexes import SearchIndex, VectorSearchIndex

from .models import SearchIndexTestModel
from .test_base import SchemaAssertionMixin


@mock.patch.object(connection.features, "supports_atlas_search", False)
class UnsupportedSearchIndexesTests(TestCase):
    def test_search_index_not_created(self):
        index = SearchIndex(name="recent_test_idx", fields=["number"])
        with connection.schema_editor() as editor, self.assertNumQueries(0):
            editor.add_index(index=index, model=SearchIndexTestModel)
        self.assertNotIn(
            index.name,
            connection.introspection.get_constraints(
                cursor=None,
                table_name=SearchIndexTestModel._meta.db_table,
            ),
        )
        with connection.schema_editor() as editor, self.assertNumQueries(0):
            editor.remove_index(index=index, model=SearchIndexTestModel)

    def test_vector_index_not_created(self):
        index = VectorSearchIndex(name="recent_test_idx", fields=["number"], similarities="cosine")
        with connection.schema_editor() as editor, self.assertNumQueries(0):
            editor.add_index(index=index, model=SearchIndexTestModel)
        self.assertNotIn(
            index.name,
            connection.introspection.get_constraints(
                cursor=None,
                table_name=SearchIndexTestModel._meta.db_table,
            ),
        )
        with connection.schema_editor() as editor, self.assertNumQueries(0):
            editor.remove_index(index=index, model=SearchIndexTestModel)


class SearchIndexTests(SimpleTestCase):
    def test_no_init_args(self):
        """All arguments must be kwargs."""
        msg = "SearchIndex.__init__() takes 1 positional argument but 2 were given"
        with self.assertRaisesMessage(TypeError, msg):
            SearchIndex("foo")

    def test_no_extra_kargs(self):
        """Unused kwargs that appear on Index aren't accepted."""
        msg = "SearchIndex.__init__() got an unexpected keyword argument 'condition'"
        with self.assertRaisesMessage(TypeError, msg):
            SearchIndex(condition="")

    def test_fields_and_field_mappings(self):
        msg = "Cannot provide fields and field_mappings."
        with self.assertRaisesMessage(ValueError, msg):
            SearchIndex(fields=["foo"], field_mappings={"foo": {}})

    def test_field_mappings_type(self):
        msg = (
            "field_mappings must be a dictionary mapping field names to their "
            "Atlas Search index options."
        )
        with self.assertRaisesMessage(ValueError, msg):
            SearchIndex(field_mappings={"foo"})

    def test_analyzer_type(self):
        msg = "analyzer must be a string; got: <class 'int'>."
        with self.assertRaisesMessage(ValueError, msg):
            SearchIndex(analyzer=42)

    def test_search_analyzer_type(self):
        msg = "search_analyzer must be a string; got: <class 'list'>."
        with self.assertRaisesMessage(ValueError, msg):
            SearchIndex(search_analyzer=["foo"])

    def test_deconstruct(self):
        index = SearchIndex(name="recent_test_idx", fields=["number"])
        name, args, kwargs = index.deconstruct()
        self.assertEqual(name, "django_mongodb_backend.indexes.SearchIndex")
        self.assertEqual(args, ())
        self.assertEqual(kwargs, {"name": "recent_test_idx", "fields": ["number"]})

    def test_deconstruct_field_mappings(self):
        field_mappings = {"headline": {"type": "token"}}
        index = SearchIndex(field_mappings=field_mappings)
        _, args, kwargs = index.deconstruct()
        self.assertEqual(args, ())
        self.assertEqual(kwargs, {"name": "", "field_mappings": field_mappings})

    def test_deconstruct_analyzer(self):
        index = SearchIndex(
            fields=["a"], analyzer="lucene.simple", search_analyzer="lucene.english"
        )
        _, args, kwargs = index.deconstruct()
        self.assertEqual(args, ())
        self.assertEqual(
            kwargs,
            {
                "name": "",
                "fields": ["a"],
                "analyzer": "lucene.simple",
                "search_analyzer": "lucene.english",
            },
        )


class VectorSearchIndexTests(SimpleTestCase):
    def test_no_init_args(self):
        """All arguments must be kwargs."""
        msg = "VectorSearchIndex.__init__() takes 1 positional argument but 2 were given"
        with self.assertRaisesMessage(TypeError, msg):
            VectorSearchIndex("foo")

    def test_no_extra_kargs(self):
        """Unused kwargs that appear on Index aren't accepted."""
        msg = "VectorSearchIndex.__init__() got an unexpected keyword argument 'condition'"
        with self.assertRaisesMessage(TypeError, msg):
            VectorSearchIndex(condition="")

    def test_similarities_required(self):
        msg = (
            "VectorSearchIndex.__init__() missing 1 required keyword-only argument: 'similarities'"
        )
        with self.assertRaisesMessage(TypeError, msg):
            VectorSearchIndex(name="recent_test_idx", fields=["number"])

    def test_deconstruct(self):
        index = VectorSearchIndex(name="recent_test_idx", fields=["number"], similarities="cosine")
        name, args, kwargs = index.deconstruct()
        self.assertEqual(name, "django_mongodb_backend.indexes.VectorSearchIndex")
        self.assertEqual(args, ())
        self.assertEqual(
            kwargs, {"name": "recent_test_idx", "fields": ["number"], "similarities": "cosine"}
        )
        new = VectorSearchIndex(*args, **kwargs)
        self.assertEqual(new.similarities, index.similarities)

    def test_invalid_similarity(self):
        msg = "'sum' isn't a valid similarity function (cosine, dotProduct, euclidean)."
        with self.assertRaisesMessage(ValueError, msg):
            VectorSearchIndex(fields=["vector_data"], similarities="sum")

    def test_invalid_similarity_in_list(self):
        msg = "'sum' isn't a valid similarity function (cosine, dotProduct, euclidean)."
        with self.assertRaisesMessage(ValueError, msg):
            VectorSearchIndex(fields=["vector_data"], similarities=["cosine", "sum"])

    def test_define_field_twice(self):
        msg = "Field 'vector_data' is duplicated in fields."
        with self.assertRaisesMessage(ValueError, msg):
            VectorSearchIndex(
                fields=["vector_data", "vector_data"],
                similarities="dotProduct",
            )


@skipUnlessDBFeature("supports_atlas_search")
class SearchIndexSchemaTests(SchemaAssertionMixin, TestCase):
    def test_simple(self):
        index = SearchIndex(name="recent_test_idx", fields=["char"])
        with connection.schema_editor() as editor:
            self.assertAddRemoveIndex(editor, index=index, model=SearchIndexTestModel)

    def test_valid_fields(self):
        index = SearchIndex(
            name="recent_test_idx",
            fields=[
                "big_integer",
                "binary",
                "char",
                "boolean",
                "datetime",
                "embedded_model",
                "float",
                "integer",
                "json",
                "object_id",
                "vector_integer",
                "vector_float",
            ],
        )
        with connection.schema_editor() as editor:
            editor.add_index(index=index, model=SearchIndexTestModel)
        try:
            index_info = connection.introspection.get_constraints(
                cursor=None,
                table_name=SearchIndexTestModel._meta.db_table,
            )
            expected_options = {
                "dynamic": False,
                "fields": {
                    "big_integer": {
                        "indexDoubles": True,
                        "indexIntegers": True,
                        "representation": "double",
                        "type": "number",
                    },
                    "binary": {
                        "indexOptions": "offsets",
                        "norms": "include",
                        "store": True,
                        "type": "string",
                    },
                    "boolean": {"type": "boolean"},
                    "char": {
                        "indexOptions": "offsets",
                        "norms": "include",
                        "store": True,
                        "type": "string",
                    },
                    "datetime": {"type": "date"},
                    "embedded_model": {"dynamic": False, "fields": {}, "type": "document"},
                    "float": {
                        "indexDoubles": True,
                        "indexIntegers": True,
                        "representation": "double",
                        "type": "number",
                    },
                    "integer": {
                        "indexDoubles": True,
                        "indexIntegers": True,
                        "representation": "double",
                        "type": "number",
                    },
                    "json": {"dynamic": False, "fields": {}, "type": "document"},
                    "object_id": {"type": "objectId"},
                    "vector_float": {"dynamic": False, "fields": {}, "type": "embeddedDocuments"},
                    "vector_integer": {"dynamic": False, "fields": {}, "type": "embeddedDocuments"},
                },
            }
            self.assertCountEqual(index_info[index.name]["columns"], index.fields)
            self.assertEqual(index_info[index.name]["options"]["mappings"], expected_options)
        finally:
            with connection.schema_editor() as editor:
                editor.remove_index(index=index, model=SearchIndexTestModel)

    def test_field_mappings(self):
        index = SearchIndex(
            name="field_mappings_test_idx",
            field_mappings={
                "char": {
                    "indexOptions": "offsets",
                    "norms": "include",
                    "store": True,
                    "type": "string",
                }
            },
        )
        with connection.schema_editor() as editor:
            editor.add_index(index=index, model=SearchIndexTestModel)
        try:
            index_info = connection.introspection.get_constraints(
                cursor=None,
                table_name=SearchIndexTestModel._meta.db_table,
            )[index.name]
            expected_options = {
                "analyzer": None,
                "searchAnalyzer": None,
                "mappings": {
                    "dynamic": False,
                    "fields": {
                        "char": {
                            "indexOptions": "offsets",
                            "norms": "include",
                            "store": True,
                            "type": "string",
                        }
                    },
                },
            }
            self.assertCountEqual(index_info["columns"], index.fields)
            self.assertEqual(index_info["options"], expected_options)
        finally:
            with connection.schema_editor() as editor:
                editor.remove_index(index=index, model=SearchIndexTestModel)

    def test_analyzer(self):
        index = SearchIndex(
            name="analyzer_test_idx",
            fields=["char"],
            analyzer="lucene.simple",
            search_analyzer="lucene.simple",
        )
        with connection.schema_editor() as editor:
            editor.add_index(index=index, model=SearchIndexTestModel)
        try:
            index_info = connection.introspection.get_constraints(
                cursor=None,
                table_name=SearchIndexTestModel._meta.db_table,
            )[index.name]
            expected_options = {
                "analyzer": "lucene.simple",
                "searchAnalyzer": "lucene.simple",
                "mappings": {
                    "dynamic": False,
                    "fields": {
                        "char": {
                            "indexOptions": "offsets",
                            "norms": "include",
                            "store": True,
                            "type": "string",
                        }
                    },
                },
            }
            self.assertCountEqual(index_info["columns"], index.fields)
            self.assertEqual(index_info["options"], expected_options)
        finally:
            with connection.schema_editor() as editor:
                editor.remove_index(index=index, model=SearchIndexTestModel)


@skipUnlessDBFeature("supports_atlas_search")
class VectorSearchIndexSchemaTests(SchemaAssertionMixin, TestCase):
    def test_simple(self):
        index = VectorSearchIndex(name="recent_test_idx", fields=["integer"], similarities="cosine")
        with connection.schema_editor() as editor:
            self.assertAddRemoveIndex(editor, index=index, model=SearchIndexTestModel)

    def test_multiple_fields(self):
        index = VectorSearchIndex(
            name="recent_test_idx",
            fields=[
                "boolean",
                "char",
                "datetime",
                "embedded_model",
                "integer",
                "object_id",
                "vector_float",
                "vector_integer",
            ],
            similarities="cosine",
        )
        with connection.schema_editor() as editor:
            editor.add_index(index=index, model=SearchIndexTestModel)
        try:
            index_info = connection.introspection.get_constraints(
                cursor=None,
                table_name=SearchIndexTestModel._meta.db_table,
            )
            expected_options = {
                "latestDefinition": {
                    "fields": [
                        {"path": "boolean", "type": "filter"},
                        {"path": "char", "type": "filter"},
                        {"path": "datetime", "type": "filter"},
                        {"path": "embedded_model", "type": "filter"},
                        {"path": "integer", "type": "filter"},
                        {"path": "object_id", "type": "filter"},
                        {
                            "numDimensions": 10,
                            "path": "vector_float",
                            "similarity": "cosine",
                            "type": "vector",
                        },
                        {
                            "numDimensions": 10,
                            "path": "vector_integer",
                            "similarity": "cosine",
                            "type": "vector",
                        },
                    ]
                },
                "latestVersion": 0,
                "name": "recent_test_idx",
                "queryable": True,
                "type": "vectorSearch",
            }
            self.assertCountEqual(index_info[index.name]["columns"], index.fields)
            index_info[index.name]["options"].pop("id")
            index_info[index.name]["options"].pop("status")
            self.assertEqual(index_info[index.name]["options"], expected_options)
        finally:
            with connection.schema_editor() as editor:
                editor.remove_index(index=index, model=SearchIndexTestModel)

    def test_similarities_list(self):
        index = VectorSearchIndex(
            name="recent_test_idx",
            fields=["vector_float", "vector_integer"],
            similarities=["cosine", "euclidean"],
        )
        with connection.schema_editor() as editor:
            editor.add_index(index=index, model=SearchIndexTestModel)
        try:
            index_info = connection.introspection.get_constraints(
                cursor=None,
                table_name=SearchIndexTestModel._meta.db_table,
            )
            expected_options = {
                "latestDefinition": {
                    "fields": [
                        {
                            "numDimensions": 10,
                            "path": "vector_float",
                            "similarity": "cosine",
                            "type": "vector",
                        },
                        {
                            "numDimensions": 10,
                            "path": "vector_integer",
                            "similarity": "euclidean",
                            "type": "vector",
                        },
                    ]
                },
                "latestVersion": 0,
                "name": "recent_test_idx",
                "queryable": True,
                "type": "vectorSearch",
            }
            self.assertCountEqual(index_info[index.name]["columns"], index.fields)
            index_info[index.name]["options"].pop("id")
            index_info[index.name]["options"].pop("status")
            self.assertEqual(index_info[index.name]["options"], expected_options)
        finally:
            with connection.schema_editor() as editor:
                editor.remove_index(index=index, model=SearchIndexTestModel)
