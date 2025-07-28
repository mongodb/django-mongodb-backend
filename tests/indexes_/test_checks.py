from unittest import mock

from django.core import checks
from django.db import connection, models
from django.test import TestCase
from django.test.utils import isolate_apps, override_system_checks

from django_mongodb_backend.checks import check_indexes
from django_mongodb_backend.fields import ArrayField, ObjectIdField
from django_mongodb_backend.indexes import SearchIndex, VectorSearchIndex
from django_mongodb_backend.models import EmbeddedModel


@isolate_apps("indexes_", attr_name="apps")
@override_system_checks([check_indexes])
@mock.patch.object(connection.features, "supports_atlas_search", False)
class UnsupportedSearchIndexesTests(TestCase):
    def test_search_requires_atlas_search_support(self):
        class Article(models.Model):
            title = models.CharField(max_length=10)

            class Meta:
                indexes = [SearchIndex(fields=["title"])]

        errors = checks.run_checks(app_configs=self.apps.get_app_configs(), databases={"default"})
        self.assertEqual(
            errors,
            [
                checks.Warning(
                    "This MongoDB server does not support SearchIndex.",
                    hint=(
                        "The index won't be created. Use an Atlas-enabled version of MongoDB, "
                        "or silence this warning if you don't care about it."
                    ),
                    obj=Article,
                    id="django_mongodb_backend.indexes.SearchIndex.W001",
                )
            ],
        )

    def test_vector_search_requires_atlas_search_support(self):
        class Article(models.Model):
            title = models.CharField(max_length=10)
            vector = ArrayField(models.FloatField(), size=10)

            class Meta:
                indexes = [VectorSearchIndex(fields=["title", "vector"], similarities="cosine")]

        errors = checks.run_checks(app_configs=self.apps.get_app_configs(), databases={"default"})
        self.assertEqual(
            errors,
            [
                checks.Warning(
                    "This MongoDB server does not support VectorSearchIndex.",
                    hint=(
                        "The index won't be created. Use an Atlas-enabled version of MongoDB, "
                        "or silence this warning if you don't care about it."
                    ),
                    obj=Article,
                    id="django_mongodb_backend.indexes.VectorSearchIndex.W001",
                )
            ],
        )


@isolate_apps("indexes_", attr_name="apps")
@override_system_checks([check_indexes])
@mock.patch.object(connection.features, "supports_atlas_search", True)
class InvalidVectorSearchIndexesTests(TestCase):
    def test_requires_size(self):
        class Article(models.Model):
            title_embedded = ArrayField(models.FloatField())

            class Meta:
                indexes = [VectorSearchIndex(fields=["title_embedded"], similarities="cosine")]

        errors = checks.run_checks(app_configs=self.apps.get_app_configs(), databases={"default"})
        self.assertEqual(
            errors,
            [
                checks.Error(
                    "VectorSearchIndex requires 'size' on field 'title_embedded'.",
                    id="django_mongodb_backend.indexes.VectorSearchIndex.E002",
                    obj=Article,
                )
            ],
        )

    def test_requires_float_inner_field(self):
        class Article(models.Model):
            title_embedded = ArrayField(models.CharField(), size=30)

            class Meta:
                indexes = [VectorSearchIndex(fields=["title_embedded"], similarities="cosine")]

        errors = checks.run_checks(app_configs=self.apps.get_app_configs(), databases={"default"})
        self.assertEqual(
            errors,
            [
                checks.Error(
                    "VectorSearchIndex requires the base field of ArrayField "
                    "'title_embedded' to be FloatField or IntegerField but is CharField.",
                    id="django_mongodb_backend.indexes.VectorSearchIndex.E003",
                    obj=Article,
                )
            ],
        )

    def test_unsupported_type(self):
        class Article(models.Model):
            data = models.JSONField()
            vector = ArrayField(models.FloatField(), size=10)

            class Meta:
                indexes = [VectorSearchIndex(fields=["data", "vector"], similarities="cosine")]

        errors = checks.run_checks(app_configs=self.apps.get_app_configs(), databases={"default"})
        self.assertEqual(
            errors,
            [
                checks.Error(
                    "VectorSearchIndex does not support field 'data' (JSONField).",
                    id="django_mongodb_backend.indexes.VectorSearchIndex.E004",
                    obj=Article,
                    hint="Allowed types are boolean, date, number, objectId, string, uuid.",
                )
            ],
        )

    def test_fields_and_similarities_mismatch(self):
        class Article(models.Model):
            vector = ArrayField(models.FloatField(), size=10)

            class Meta:
                indexes = [
                    VectorSearchIndex(
                        fields=["vector"],
                        similarities=["dotProduct", "cosine"],
                    )
                ]

        errors = checks.run_checks(app_configs=self.apps.get_app_configs(), databases={"default"})
        self.assertEqual(
            errors,
            [
                checks.Error(
                    "VectorSearchIndex requires the same number of similarities "
                    "and vector fields; Article has 1 ArrayField(s) but similarities "
                    "has 2 element(s).",
                    id="django_mongodb_backend.indexes.VectorSearchIndex.E005",
                    obj=Article,
                ),
            ],
        )

    def test_simple(self):
        class Article(models.Model):
            vector = ArrayField(models.FloatField(), size=10)

            class Meta:
                indexes = [VectorSearchIndex(fields=["vector"], similarities="cosine")]

        errors = checks.run_checks(app_configs=self.apps.get_app_configs(), databases={"default"})
        self.assertEqual(errors, [])

    def test_valid_fields(self):
        class Data(EmbeddedModel):
            integer = models.IntegerField()

        class SearchIndexTestModel(models.Model):
            text = models.CharField(max_length=100)
            object_id = ObjectIdField()
            number = models.IntegerField()
            vector_integer = ArrayField(models.IntegerField(), size=10)
            vector_float = ArrayField(models.FloatField(), size=10)
            boolean = models.BooleanField()
            date = models.DateTimeField(auto_now=True)

            class Meta:
                indexes = [
                    VectorSearchIndex(
                        name="recent_test_idx",
                        fields=[
                            "text",
                            "object_id",
                            "number",
                            "vector_integer",
                            "vector_float",
                            "boolean",
                            "date",
                        ],
                        similarities="cosine",
                    )
                ]

        errors = checks.run_checks(app_configs=self.apps.get_app_configs(), databases={"default"})
        self.assertEqual(errors, [])

    def test_requires_vector_field(self):
        class NoSearchVectorModel(models.Model):
            text = models.CharField(max_length=100)

            class Meta:
                indexes = [
                    VectorSearchIndex(
                        name="recent_test_idx", fields=["text"], similarities="cosine"
                    )
                ]

        errors = checks.run_checks(app_configs=self.apps.get_app_configs(), databases={"default"})
        self.assertEqual(
            errors,
            [
                checks.Error(
                    "VectorSearchIndex requires at least one ArrayField to store vector data.",
                    id="django_mongodb_backend.indexes.VectorSearchIndex.E006",
                    obj=NoSearchVectorModel,
                    hint="If you want to perform search operations without vectors, "
                    "use SearchIndex instead.",
                ),
            ],
        )
