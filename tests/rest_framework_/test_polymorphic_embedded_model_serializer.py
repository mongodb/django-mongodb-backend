import unittest

try:
    import rest_framework  # noqa: F401
except ImportError:
    raise unittest.SkipTest("djangorestframework not installed") from None

from django.test import SimpleTestCase, TestCase
from rest_framework import serializers

from django_mongodb_backend.rest_framework import PolymorphicEmbeddedModelSerializer

from .models import Cat, Dog, PetOwner
from .serializers import PetOwnerSerializer


class PolymorphicEmbeddedModelSerializerTests(SimpleTestCase):
    def test_polymorphic_field_is_read_only(self):
        fields = PetOwnerSerializer().get_fields()
        self.assertTrue(fields["pet"].read_only)

    def test_polymorphic_array_field_is_read_only(self):
        fields = PetOwnerSerializer().get_fields()
        self.assertTrue(fields["pets"].read_only)

    def test_polymorphic_field_is_polymorphic_serializer(self):
        fields = PetOwnerSerializer().get_fields()
        self.assertIsInstance(fields["pet"], PolymorphicEmbeddedModelSerializer)

    def test_polymorphic_array_field_is_list_serializer(self):
        fields = PetOwnerSerializer().get_fields()
        self.assertIsInstance(fields["pets"], serializers.ListSerializer)
        self.assertIsInstance(fields["pets"].child, PolymorphicEmbeddedModelSerializer)

    def test_to_representation_dog(self):
        owner = PetOwner(name="Alice", pet=Dog(name="Rex", barks=True), pets=None)
        data = PetOwnerSerializer(owner).data
        self.assertEqual(data["pet"], {"name": "Rex", "barks": True})

    def test_to_representation_cat(self):
        owner = PetOwner(name="Bob", pet=Cat(name="Whiskers", purrs=True), pets=None)
        data = PetOwnerSerializer(owner).data
        self.assertEqual(data["pet"], {"name": "Whiskers", "purrs": True})

    def test_to_representation_array_mixed_types(self):
        owner = PetOwner(
            name="Carol",
            pet=None,
            pets=[Dog(name="Rex", barks=True), Cat(name="Luna", purrs=False)],
        )
        data = PetOwnerSerializer(owner).data
        self.assertEqual(data["pets"][0], {"name": "Rex", "barks": True})
        self.assertEqual(data["pets"][1], {"name": "Luna", "purrs": False})

    def test_to_representation_null(self):
        owner = PetOwner(name="Dave", pet=None, pets=None)
        data = PetOwnerSerializer(owner).data
        self.assertIsNone(data["pet"])


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
