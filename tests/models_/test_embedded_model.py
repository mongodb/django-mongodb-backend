from django.core import checks
from django.db import NotSupportedError, models
from django.test import SimpleTestCase
from django.test.utils import isolate_apps

from django_mongodb_backend.models import EmbeddedModel

from .models import Embed


class TestMethods(SimpleTestCase):
    def test_save(self):
        e = Embed()
        with self.assertRaisesMessage(NotSupportedError, "EmbeddedModels cannot be saved."):
            e.save()

    def test_delete(self):
        e = Embed()
        with self.assertRaisesMessage(NotSupportedError, "EmbeddedModels cannot be deleted."):
            e.delete()


@isolate_apps("models_")
class TestChecks(SimpleTestCase):
    def test_db_index(self):
        class Target(EmbeddedModel):
            foo = models.IntegerField(db_index=True)

        errors = Target().check()
        self.assertEqual(
            errors,
            [
                checks.Warning(
                    "Using db_index=True on embedded fields is deprecated "
                    "in favor of using EmbeddedFieldIndex in Meta.indexes "
                    "on the top-level model.",
                    id="mongodb.fields.embedded_model.W004",
                    obj=Target._meta.get_field("foo"),
                )
            ],
        )

    def test_unique(self):
        class Target(EmbeddedModel):
            foo = models.IntegerField(unique=True)

        errors = Target().check()
        self.assertEqual(
            errors,
            [
                checks.Warning(
                    "Using unique=True on embedded fields is deprecated "
                    "in favor of using EmbeddedFieldUniqueConstraint in "
                    "Meta.constraints on the top-level model.",
                    id="mongodb.fields.embedded_model.W005",
                    obj=Target._meta.get_field("foo"),
                )
            ],
        )

    def test_constraints(self):
        class Target(EmbeddedModel):
            foo = models.IntegerField()

            class Meta:
                constraints = [models.UniqueConstraint(fields=["foo"], name="name")]

        errors = Target().check()
        self.assertEqual(
            errors,
            [
                checks.Warning(
                    "Using Meta.constraints on embedded models is deprecated "
                    "in favor of using EmbeddedFieldUniqueConstraint in "
                    "Meta.constraints on the top-level model.",
                    id="mongodb.fields.embedded_model.W006",
                    obj=Target,
                )
            ],
        )

    def test_indexes(self):
        class Target(EmbeddedModel):
            foo = models.IntegerField()

            class Meta:
                indexes = [models.Index(fields=["foo"])]

        errors = Target().check()
        self.assertEqual(
            errors,
            [
                checks.Warning(
                    "Using Meta.indexes on embedded models is deprecated in "
                    "favor of using EmbeddedFieldIndex in Meta.indexes on the "
                    "top-level model.",
                    id="mongodb.fields.embedded_model.W007",
                    obj=Target,
                )
            ],
        )

    def test_unique_together(self):
        class Target(EmbeddedModel):
            a = models.IntegerField()
            b = models.IntegerField()

            class Meta:
                unique_together = ["a", "b"]

        errors = Target().check()
        self.assertEqual(
            errors,
            [
                checks.Warning(
                    "Using Meta.unique_together on embedded models is "
                    "deprecated in favor of using EmbeddedFieldUniqueConstraint "
                    "in Meta.constraints on the top-level model.",
                    id="mongodb.fields.embedded_model.W008",
                    obj=Target,
                )
            ],
        )


class TestManagerMethods(SimpleTestCase):
    def test_all(self):
        with self.assertRaisesMessage(NotSupportedError, "EmbeddedModels cannot be queried."):
            Embed.objects.all()

    def test_get(self):
        with self.assertRaisesMessage(NotSupportedError, "EmbeddedModels cannot be queried."):
            Embed.objects.get(foo="bar")

    def test_filter(self):
        with self.assertRaisesMessage(NotSupportedError, "EmbeddedModels cannot be queried."):
            Embed.objects.filter(foo="bar")

    def test_create(self):
        with self.assertRaisesMessage(NotSupportedError, "EmbeddedModels cannot be created."):
            Embed.objects.create(foo="bar")

    def test_update(self):
        with self.assertRaisesMessage(NotSupportedError, "EmbeddedModels cannot be updated."):
            Embed.objects.update(foo="bar")

    def test_delete(self):
        with self.assertRaisesMessage(NotSupportedError, "EmbeddedModels cannot be deleted."):
            Embed.objects.delete()

    def test_get_or_create(self):
        msg = "'EmbeddedModelManager' object has no attribute 'get_or_create'"
        with self.assertRaisesMessage(AttributeError, msg):
            Embed.objects.get_or_create()
