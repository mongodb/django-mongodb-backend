from django.core import checks
from django.db import models
from django.test import TestCase, skipIfDBFeature, skipUnlessDBFeature
from django.test.utils import (
    isolate_apps,
    override_system_checks,
)

from django_mongodb_backend.checks import check_indexes
from django_mongodb_backend.fields import ArrayField
from django_mongodb_backend.indexes import SearchIndex, VectorSearchIndex


@skipIfDBFeature("supports_atlas_search")
@isolate_apps("indexes_", attr_name="apps")
@override_system_checks([check_indexes])
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
                    "This MongoDB server does not support atlas search.",
                    hint=(
                        "The index won't be created. Silence this warning if you "
                        "don't care about it."
                    ),
                    obj=Article._meta.indexes[0],
                    id="django_mongodb_backend.indexes.SearchIndex.W001",
                )
            ],
        )

    def test_vector_search_requires_atlas_search_support(self):
        class Article(models.Model):
            title = models.CharField(max_length=10)

            class Meta:
                indexes = [VectorSearchIndex(fields=["title"])]

        errors = checks.run_checks(app_configs=self.apps.get_app_configs(), databases={"default"})
        self.assertEqual(
            errors,
            [
                checks.Warning(
                    "This MongoDB server does not support atlas search.",
                    hint=(
                        "The index won't be created. Silence this warning if you "
                        "don't care about it."
                    ),
                    obj=Article._meta.indexes[0],
                    id="django_mongodb_backend.indexes.VectorSearchIndex.W001",
                )
            ],
        )


@skipUnlessDBFeature("supports_atlas_search")
@isolate_apps("indexes_", attr_name="apps")
@override_system_checks([check_indexes])
class InvalidVectorSearchIndexesTests(TestCase):
    def test_requires_size(self):
        class Article(models.Model):
            title_embedded = ArrayField(models.FloatField())

            class Meta:
                indexes = [VectorSearchIndex(fields=["title_embedded"])]

        errors = checks.run_checks(app_configs=self.apps.get_app_configs(), databases={"default"})
        self.assertEqual(
            errors,
            [
                checks.Error(
                    "Atlas vector search requires size on title_embedded.",
                    id="django_mongodb_backend.indexes.VectorSearchIndex.E001",
                    obj=Article._meta.indexes[0],
                )
            ],
        )

    def test_requires_float_inner_field(self):
        class Article(models.Model):
            title_embedded = ArrayField(models.CharField(), size=30)

            class Meta:
                indexes = [VectorSearchIndex(fields=["title_embedded"])]

        errors = checks.run_checks(app_configs=self.apps.get_app_configs(), databases={"default"})
        self.assertEqual(
            errors,
            [
                checks.Error(
                    "An Atlas vector search index requires the base field of ArrayField "
                    "Model.field_name to be FloatField or DecimalField but is CharField.",
                    id="django_mongodb_backend.indexes.VectorSearchIndex.E002",
                    obj=Article._meta.indexes[0],
                )
            ],
        )

    def test_unsupported_type(self):
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

    def test_define_field_twice(self):
        class Article(models.Model):
            vector_data = ArrayField(models.DecimalField(), size=10)

            class Meta:
                indexes = [
                    VectorSearchIndex(
                        fields=["vector_data", "vector_data"],
                        similarities="dotProduct",
                    )
                ]

        errors = checks.run_checks(app_configs=self.apps.get_app_configs(), databases={"default"})
        self.assertEqual(
            errors,
            [
                checks.Error(
                    "Field 'vector_data' is defined more than once. Vector and filter "
                    "fields must use distinct field names.",
                    id="django_mongodb_backend.indexes.VectorSearchIndex.E004",
                    hint="If you need different configurations for the same field, "
                    "create separate indexes.",
                    obj=Article._meta.indexes[0],
                ),
            ],
        )

    def test_invalid_number_similarity_function_singular(self):
        class Article(models.Model):
            vector_data = ArrayField(models.DecimalField(), size=10)

            class Meta:
                indexes = [
                    VectorSearchIndex(
                        fields=["vector_data"],
                        similarities=["dotProduct", "cosine"],
                    )
                ]

        errors = checks.run_checks(app_configs=self.apps.get_app_configs(), databases={"default"})
        self.assertEqual(
            errors,
            [
                checks.Error(
                    "An Atlas vector search index requires the same number of similarities "
                    "and vector fields, but 1 similarity function were expected and 2 "
                    "were provided.",
                    id="django_mongodb_backend.indexes.VectorSearchIndex.E005",
                    obj=Article._meta.indexes[0],
                ),
            ],
        )

    def test_invalid_number_similarity_function_plural(self):
        class Article(models.Model):
            vector1 = ArrayField(models.DecimalField(), size=10)
            vector2 = ArrayField(models.DecimalField(), size=10)

            class Meta:
                indexes = [
                    VectorSearchIndex(
                        fields=["vector1", "vector2"],
                        similarities=["dotProduct"],
                    )
                ]

        errors = checks.run_checks(app_configs=self.apps.get_app_configs(), databases={"default"})
        self.assertEqual(
            errors,
            [
                checks.Error(
                    "An Atlas vector search index requires the same number of similarities "
                    "and vector fields, but 2 similarities functions were expected and 1 "
                    "was provided.",
                    id="django_mongodb_backend.indexes.VectorSearchIndex.E005",
                    obj=Article._meta.indexes[0],
                ),
            ],
        )

    def test_simple(self):
        class Article(models.Model):
            vector_data = ArrayField(models.DecimalField(), size=10)

            class Meta:
                indexes = [VectorSearchIndex(fields=["vector_data"])]

        errors = checks.run_checks(app_configs=self.apps.get_app_configs(), databases={"default"})
        self.assertEqual(errors, [])
