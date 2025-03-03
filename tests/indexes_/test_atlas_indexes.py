import datetime

from django.core.exceptions import FieldDoesNotExist
from django.db import connection
from django.test import TestCase

from django_mongodb_backend.indexes import AtlasSearchIndex, AtlasVectorSearchIndex

from .models import Article, Data


class AtlasIndexTests(TestCase):
    # Schema editor is used to  create the index to test that it works.
    # available_apps = ["indexes"]
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
            index = AtlasSearchIndex(
                name="recent_article_idx",
                fields=["number"],
            )
            editor.add_index(index=index, model=Article)
            self.assertAddRemoveIndex(editor, Article, index)

    def test_multiple_fields(self):
        with connection.schema_editor() as editor:
            index = AtlasSearchIndex(
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

    def test_field_not_exists(self):
        index = AtlasSearchIndex(
            name="recent_article_idx",
            fields=["headline", "number1"],
        )
        with connection.schema_editor() as editor:
            msg = "Article has no field named 'number1'"
            with self.assertRaisesMessage(
                FieldDoesNotExist, msg
            ), connection.schema_editor() as editor:
                editor.add_index(index=index, model=Article)


class AtlasIndexTestsWithData(AtlasIndexTests):
    @classmethod
    def setUpTestData(cls):
        articles = [
            Article(
                headline=f"Title {i}",
                number=i,
                body=f"body {i}",
                data="{json: i}",
                embedded=Data(integer=i),
                auto_now=datetime.datetime.now(),
                title_embedded=[0.1] * 10,
                description_embedded=[2.5] * 10,
                number_list=[2] * i,
                name_list=[f"name_{i}"] * 10,
            )
            for i in range(5)
        ]
        cls.objs = Article.objects.bulk_create(articles)


class AtlasSearchIndexTests(TestCase):
    # Schema editor is used to  create the index to test that it works.
    # available_apps = ["indexes"]
    available_apps = None  # could be removed?

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

    def test_simple_atlas_vector_search(self):
        with connection.schema_editor() as editor:
            index = AtlasVectorSearchIndex(
                name="recent_article_idx",
                fields=["number"],
            )
            editor.add_index(index=index, model=Article)
            self.assertAddRemoveIndex(editor, Article, index)

    def test_multiple_fields(self):
        with connection.schema_editor() as editor:
            index = AtlasVectorSearchIndex(
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

    def test_field_not_exists(self):
        index = AtlasVectorSearchIndex(
            name="recent_article_idx",
            fields=["headline", "number1", "title_embedded"],
        )
        with connection.schema_editor() as editor:
            msg = "Article has no field named 'number1'"
            with self.assertRaisesMessage(
                FieldDoesNotExist, msg
            ), connection.schema_editor() as editor:
                editor.add_index(index=index, model=Article)


class AtlasSearchIndexTestsWithData(AtlasSearchIndexTests):
    @classmethod
    def setUpTestData(cls):
        articles = [
            Article(
                headline=f"Title {i}",
                number=i,
                body=f"body {i}",
                data="{json: i}",
                embedded=Data(integer=i),
                auto_now=datetime.datetime.now(),
                title_embedded=[0.1] * 10,
                description_embedded=[2.5] * 10,
                number_list=[2] * i,
                name_list=[f"name_{i}"] * 10,
            )
            for i in range(5)
        ]
        cls.objs = Article.objects.bulk_create(articles)
