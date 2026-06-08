import unittest

try:
    import rest_framework  # noqa: F401
except ImportError:
    raise unittest.SkipTest("djangorestframework not installed") from None

from django.test import TestCase

from django_mongodb_backend.rest_framework import MongoModelSerializer

from .models import Cat, Dog, PetOwner


class PetOwnerSerializer(MongoModelSerializer):
    class Meta:
        model = PetOwner
        fields = "__all__"


class PolymorphicEmbeddedModelSerializerReadTests(TestCase):
    def test_read_polymorphic_field_dog(self):
        original = PetOwner.objects.create(name="Alice", pet=Dog(name="Rex", barks=True), pets=None)
        loaded = PetOwner.objects.get(pk=original.pk)
        data = PetOwnerSerializer(loaded).data
        self.assertEqual(data["name"], "Alice")
        self.assertEqual(data["pet"], {"name": "Rex", "barks": True})
        self.assertIsNone(data["pets"])

    def test_read_polymorphic_field_cat(self):
        original = PetOwner.objects.create(
            name="Bob", pet=Cat(name="Whiskers", purrs=False), pets=None
        )
        loaded = PetOwner.objects.get(pk=original.pk)
        data = PetOwnerSerializer(loaded).data
        self.assertEqual(data["pet"], {"name": "Whiskers", "purrs": False})

    def test_read_polymorphic_array_field_mixed_types(self):
        original = PetOwner.objects.create(
            name="Carol",
            pet=None,
            pets=[Dog(name="Rex", barks=True), Cat(name="Luna", purrs=True)],
        )
        loaded = PetOwner.objects.get(pk=original.pk)
        data = PetOwnerSerializer(loaded).data
        self.assertIsNone(data["pet"])
        self.assertEqual(len(data["pets"]), 2)
        self.assertEqual(data["pets"][0], {"name": "Rex", "barks": True})
        self.assertEqual(data["pets"][1], {"name": "Luna", "purrs": True})

    def test_read_polymorphic_fields_null(self):
        original = PetOwner.objects.create(name="Dave", pet=None, pets=None)
        loaded = PetOwner.objects.get(pk=original.pk)
        data = PetOwnerSerializer(loaded).data
        self.assertIsNone(data["pet"])
        self.assertIsNone(data["pets"])
