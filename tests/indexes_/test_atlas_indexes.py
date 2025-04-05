from django.db import connection
from django.test import TestCase

from django_mongodb_backend.indexes import SearchIndex, VectorSearchIndex

from .models import Article


class SearchIndexTests(TestCase):
    # Tests for creating, validating, and removing search indexes using Django's schema editor.
    available_apps = None

    def assertAddRemoveIndex(self, editor, model, index):
        editor.add_index(index=index, model=model)
        self.assertIn(
            index.name,
            connection.introspection.get_constraints(
                cursor=None,
                table_name=model._meta.db_table,
            ),
        )
        editor.remove_index(index=index, model=model)
        self.assertNotIn(
            index.name,
            connection.introspection.get_constraints(
                cursor=None,
                table_name=model._meta.db_table,
            ),
        )

    def test_simple(self):
        with connection.schema_editor() as editor:
            index = SearchIndex(
                name="recent_article_idx",
                fields=["number"],
            )
            editor.add_index(index=index, model=Article)
            self.assertAddRemoveIndex(editor, Article, index)

    def test_multiple_fields(self):
        with connection.schema_editor() as editor:
            index = SearchIndex(
                name="recent_article_idx",
                fields=["headline", "number", "body", "data", "embedded", "auto_now"],
            )
            editor.add_index(index=index, model=Article)
            index_info = connection.introspection.get_constraints(
                cursor=None,
                table_name=Article._meta.db_table,
            )
            expected_options = {
                "dynamic": False,
                "fields": {
                    "auto_now": {"type": "date"},
                    "body": {
                        "indexOptions": "offsets",
                        "norms": "include",
                        "store": True,
                        "type": "string",
                    },
                    "data": {"dynamic": False, "fields": {}, "type": "document"},
                    "embedded": {"dynamic": False, "fields": {}, "type": "embeddedDocuments"},
                    "headline": {
                        "indexOptions": "offsets",
                        "norms": "include",
                        "store": True,
                        "type": "string",
                    },
                    "number": {
                        "indexDoubles": True,
                        "indexIntegers": True,
                        "representation": "double",
                        "type": "number",
                    },
                },
            }
            self.assertCountEqual(index_info[index.name]["columns"], index.fields)
            self.assertEqual(index_info[index.name]["options"], expected_options)
            self.assertAddRemoveIndex(editor, Article, index)


class VectorSearchIndexTests(TestCase):
    # Tests for creating, validating, and removing vector search indexes
    # using Django's schema editor.
    available_apps = None

    def assertAddRemoveIndex(self, editor, model, index):
        editor.add_index(index=index, model=model)
        self.assertIn(
            index.name,
            connection.introspection.get_constraints(
                cursor=None,
                table_name=model._meta.db_table,
            ),
        )
        editor.remove_index(index=index, model=model)
        self.assertNotIn(
            index.name,
            connection.introspection.get_constraints(
                cursor=None,
                table_name=model._meta.db_table,
            ),
        )

    def test_deconstruct_default_similarity(self):
        index = VectorSearchIndex(
            name="recent_article_idx",
            fields=["number"],
        )
        name, args, kwargs = index.deconstruct()
        new = VectorSearchIndex(*args, **kwargs)
        self.assertEqual(new.similarities, index.similarities)

    def test_deconstruct_with_similarities(self):
        index = VectorSearchIndex(
            name="recent_article_idx",
            fields=["number", "number"],
            similarities=["cosine", "dotProduct"],
        )
        path, args, kwargs = index.deconstruct()
        new = VectorSearchIndex(*args, **kwargs)
        self.assertEqual(new.similarities, index.similarities)

    def test_simple_vector_search(self):
        with connection.schema_editor() as editor:
            index = VectorSearchIndex(
                name="recent_article_idx",
                fields=["number"],
            )
            editor.add_index(index=index, model=Article)
            self.assertAddRemoveIndex(editor, Article, index)

    def test_multiple_fields(self):
        with connection.schema_editor() as editor:
            index = VectorSearchIndex(
                name="recent_article_idx",
                fields=["headline", "number", "body", "description_embedded"],
            )
            editor.add_index(index=index, model=Article)
            index_info = connection.introspection.get_constraints(
                cursor=None,
                table_name=Article._meta.db_table,
            )
            expected_options = {
                "latestDefinition": {
                    "fields": [
                        {"path": "headline", "type": "filter"},
                        {"path": "number", "type": "filter"},
                        {"path": "body", "type": "filter"},
                        {
                            "numDimensions": 10,
                            "path": "description_embedded",
                            "similarity": "cosine",
                            "type": "vector",
                        },
                    ]
                },
                "latestVersion": 0,
                "name": "recent_article_idx",
                "queryable": False,
                "type": "vectorSearch",
            }
            self.assertCountEqual(index_info[index.name]["columns"], index.fields)
            index_info[index.name]["options"].pop("id")
            index_info[index.name]["options"].pop("status")
            self.assertEqual(index_info[index.name]["options"], expected_options)
            self.assertAddRemoveIndex(editor, Article, index)
