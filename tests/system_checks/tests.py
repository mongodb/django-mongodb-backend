from django.core import checks
from django.db import models
from django.test import SimpleTestCase
from django.test.utils import (
    isolate_apps,
    override_system_checks,
)

from django_mongodb_backend.checks import check_vector_search_indexes
from django_mongodb_backend.fields import ArrayField
from django_mongodb_backend.indexes import VectorSearchIndex


@isolate_apps("system_checks", attr_name="apps")
@override_system_checks([check_vector_search_indexes])
class InvalidSearchIndexesTest(SimpleTestCase):
    def test_vectorsearch_requires_size(self):
        class Article(models.Model):
            title_embedded = ArrayField(models.FloatField())

            class Meta:
                indexes = [
                    VectorSearchIndex(fields=["title_embedded"]),
                ]

        errors = checks.run_checks(app_configs=self.apps.get_app_configs(), databases={"default"})
        self.assertEqual(
            errors,
            [
                checks.Error(
                    "Atlas vector search requires size.",
                    id="django_mongodb_backend.indexes.VectorSearchIndex.E001",
                    obj=Article._meta.indexes[0],
                )
            ],
        )

    def test_vectorsearch_requires_float_inner_field(self):
        class Article(models.Model):
            title_embedded = ArrayField(models.CharField(), size=30)

            class Meta:
                indexes = [
                    VectorSearchIndex(fields=["title_embedded"]),
                ]

        errors = checks.run_checks(app_configs=self.apps.get_app_configs(), databases={"default"})
        self.assertEqual(
            errors,
            [
                checks.Error(
                    "Base type must be Float or Decimal.",
                    id="django_mongodb_backend.indexes.VectorSearchIndex.E002",
                    obj=Article._meta.indexes[0],
                )
            ],
        )

    def test_vectorsearch_unsupported_type(self):
        class Article(models.Model):
            data = models.JSONField()

            class Meta:
                indexes = [
                    VectorSearchIndex(fields=["data"]),
                ]

        errors = checks.run_checks(app_configs=self.apps.get_app_configs(), databases={"default"})
        self.assertEqual(
            errors,
            [
                checks.Error(
                    "Unsupported filter of type JSONField.",
                    id="django_mongodb_backend.indexes.VectorSearchIndex.E003",
                    obj=Article._meta.indexes[0],
                )
            ],
        )

    def test_vectorsearch(self):
        class Article(models.Model):
            vector_data = ArrayField(models.DecimalField(), size=10)

            class Meta:
                indexes = [
                    VectorSearchIndex(fields=["vector_data"]),
                ]

        errors = checks.run_checks(app_configs=self.apps.get_app_configs(), databases={"default"})
        self.assertEqual(errors, [])
