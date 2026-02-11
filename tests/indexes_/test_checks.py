from unittest import mock

from django.core import checks
from django.db import connection, models
from django.test import TestCase
from django.test.utils import isolate_apps

from django_mongodb_backend.fields import ArrayField, ObjectIdField
from django_mongodb_backend.indexes import (
    EmbeddedFieldIndex,
    SearchIndex,
    VectorSearchIndex,
)
from django_mongodb_backend.models import EmbeddedModel

from .models import DataHolder, Movie, Owner, Person, Store


@isolate_apps("indexes_")
@mock.patch.object(connection.features, "supports_atlas_search", False)
class UnsupportedSearchIndexesTests(TestCase):
    def test_search_requires_atlas_search_support(self):
        class Article(models.Model):
            title = models.CharField(max_length=10)

            class Meta:
                indexes = [SearchIndex(fields=["title"])]

        self.assertEqual(
            Article.check(databases={"default"}),
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

        self.assertEqual(
            Article.check(databases={"default"}),
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


@isolate_apps("indexes_")
@mock.patch.object(connection.features, "supports_atlas_search", True)
class InvalidVectorSearchIndexesTests(TestCase):
    def test_requires_size(self):
        class Article(models.Model):
            title_embedded = ArrayField(models.FloatField())

            class Meta:
                indexes = [VectorSearchIndex(fields=["title_embedded"], similarities="cosine")]

        self.assertEqual(
            Article.check(databases={"default"}),
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
            title_embedded = ArrayField(models.CharField(max_length=1), size=30)

            class Meta:
                indexes = [VectorSearchIndex(fields=["title_embedded"], similarities="cosine")]

        self.assertEqual(
            Article.check(databases={"default"}),
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

        self.assertEqual(
            Article.check(databases={"default"}),
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

        self.assertEqual(
            Article.check(databases={"default"}),
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

        self.assertEqual(Article.check(databases={"default"}), [])

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

        self.assertEqual(SearchIndexTestModel.check(databases={"default"}), [])

    def test_requires_vector_field(self):
        class NoSearchVectorModel(models.Model):
            text = models.CharField(max_length=100)

            class Meta:
                indexes = [
                    VectorSearchIndex(
                        name="recent_test_idx", fields=["text"], similarities="cosine"
                    )
                ]

        self.assertEqual(
            NoSearchVectorModel.check(databases={"default"}),
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


@isolate_apps("indexes_")
class EmbeddedFieldIndexChecksTests(TestCase):
    def test_valid_embedded_model_subfield(self):
        index = EmbeddedFieldIndex(name="name", fields=["data.integer"])
        errors = index.check(DataHolder, connection=connection)
        self.assertEqual(errors, [])

    def test_nonexistent_embedded_model_subfield(self):
        index = EmbeddedFieldIndex(
            name="name",
            fields=[
                "data.field_does_not_exist",
                "another_non_existing",
                "data.integer",
            ],
        )
        errors = index.check(DataHolder, connection=connection)
        self.assertEqual(len(errors), 2)
        self.assertEqual(errors[0].id, "models.E012")
        self.assertEqual(
            errors[0].msg,
            "'indexes' refers to the nonexistent field 'data.field_does_not_exist'.",
        )
        self.assertEqual(errors[1].id, "models.E012")
        self.assertEqual(
            errors[1].msg, "'indexes' refers to the nonexistent field 'another_non_existing'."
        )

    def test_valid_embedded_model_array_subfield(self):
        index = EmbeddedFieldIndex(name="name", fields=["reviews.title"])
        errors = index.check(Movie, connection=connection)
        self.assertEqual(errors, [])

    def test_nonexistent_embedded_model_array_subfield(self):
        index = EmbeddedFieldIndex(
            name="name",
            fields=["reviews.author", "non_existing", "reviews.title"],
        )
        errors = index.check(Movie, connection=connection)
        self.assertEqual(len(errors), 2)
        self.assertEqual(errors[0].id, "models.E012")
        self.assertEqual(
            errors[0].msg,
            "'indexes' refers to the nonexistent field 'reviews.author'.",
        )
        self.assertEqual(errors[1].id, "models.E012")
        self.assertEqual(errors[1].msg, "'indexes' refers to the nonexistent field 'non_existing'.")

    def test_valid_polymorphic_embedded_model_subfield(self):
        index = EmbeddedFieldIndex(name="name", fields=["pet.name"])
        errors = index.check(Person, connection=connection)
        self.assertEqual(errors, [])

    def test_nonexistent_polymorphic_embedded_model_subfield(self):
        index = EmbeddedFieldIndex(name="name", fields=["pet.non_existing"])
        errors = index.check(Person, connection=connection)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].id, "models.E012")
        self.assertEqual(
            errors[0].msg,
            "'indexes' refers to the nonexistent field 'pet.non_existing'.",
        )

    def test_valid_polymorphic_embedded_model_array_subfield(self):
        index = EmbeddedFieldIndex(name="name", fields=["pets.name"])
        errors = index.check(Owner, connection=connection)
        self.assertEqual(errors, [])

    def test_nonexistent_polymorphic_embedded_model_array_subfield(self):
        index = EmbeddedFieldIndex(name="name", fields=["pets.non_existing"])
        errors = index.check(Owner, connection=connection)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].id, "models.E012")
        self.assertEqual(
            errors[0].msg,
            "'indexes' refers to the nonexistent field 'pets.non_existing'.",
        )

    def test_valid_nested_polymorphic_subfield(self):
        index = EmbeddedFieldIndex(name="name", fields=["thing.tags.name"])
        errors = index.check(Store, connection=connection)
        self.assertEqual(errors, [])

    def test_nonexistent_nested_polymorphic_subfield(self):
        index = EmbeddedFieldIndex(name="name", fields=["thing.tags.xxx"])
        errors = index.check(Store, connection=connection)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].id, "models.E012")
        self.assertEqual(
            errors[0].msg,
            "'indexes' refers to the nonexistent field 'thing.tags.xxx'.",
        )
