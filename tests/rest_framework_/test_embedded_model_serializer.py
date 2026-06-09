import unittest

try:
    import rest_framework  # noqa: F401
except ImportError:
    raise unittest.SkipTest("djangorestframework not installed") from None

from django.core.exceptions import FieldDoesNotExist
from django.test import SimpleTestCase
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from django_mongodb_backend.rest_framework import EmbeddedModelSerializer, MongoModelSerializer

from .models import City, CityWithUniqueCode, Continent, Country
from .serializers import CitySerializer, CountrySerializer, StatusTagSerializer


class EmbeddedModelSerializerToRepresentationTests(SimpleTestCase):
    def test_basic(self):
        city = City(name="Paris", population=2_000_000)
        data = CitySerializer(city).data
        self.assertEqual(data, {"name": "Paris", "population": 2_000_000})

    def test_nested_embedded_field(self):
        capital = City(name="Berlin", population=3_500_000)
        country = Country(name="Germany", capital=capital, cities=None, languages=None)
        data = CountrySerializer(country).data
        self.assertEqual(
            data,
            {
                "name": "Germany",
                "capital": {"name": "Berlin", "population": 3_500_000},
                "cities": None,
                "languages": None,
            },
        )

    def test_nested_embedded_array_field(self):
        cities = [City(name="Lyon", population=500_000), City(name="Nice", population=340_000)]
        country = Country(name="France", capital=None, cities=cities, languages=["French"])
        data = CountrySerializer(country).data
        self.assertEqual(
            data,
            {
                "name": "France",
                "capital": None,
                "cities": [
                    {"name": "Lyon", "population": 500_000},
                    {"name": "Nice", "population": 340_000},
                ],
                "languages": ["French"],
            },
        )

    def test_null_embedded_field(self):
        country = Country(name="Iceland", capital=None, cities=None, languages=None)
        data = CountrySerializer(country).data
        self.assertIsNone(data["capital"])

    def test_array_field(self):
        country = Country(name="Belgium", capital=None, cities=None, languages=["French", "Dutch"])
        data = CountrySerializer(country).data
        self.assertEqual(data["languages"], ["French", "Dutch"])


class EmbeddedModelSerializerToInternalValueTests(SimpleTestCase):
    def test_basic(self):
        s = CitySerializer(data={"name": "Tokyo", "population": 13_000_000})
        self.assertTrue(s.is_valid(), s.errors)
        result = s.validated_data
        self.assertIsInstance(result, City)
        self.assertEqual(result.name, "Tokyo")
        self.assertEqual(result.population, 13_000_000)

    def test_nested_embedded_field(self):
        data = {
            "name": "Japan",
            "capital": {"name": "Tokyo", "population": 13_000_000},
            "cities": None,
            "languages": None,
        }
        s = CountrySerializer(data=data)
        self.assertTrue(s.is_valid(), s.errors)
        result = s.validated_data
        self.assertIsInstance(result, Country)
        self.assertIsInstance(result.capital, City)
        self.assertEqual(result.capital.name, "Tokyo")

    def test_nested_embedded_array_field(self):
        data = {
            "name": "Italy",
            "capital": None,
            "cities": [
                {"name": "Rome", "population": 2_800_000},
                {"name": "Milan", "population": 1_300_000},
            ],
            "languages": ["Italian"],
        }
        s = CountrySerializer(data=data)
        self.assertTrue(s.is_valid(), s.errors)
        result = s.validated_data
        self.assertIsInstance(result, Country)
        self.assertEqual(len(result.cities), 2)
        self.assertIsInstance(result.cities[0], City)
        self.assertEqual(result.cities[0].name, "Rome")

    def test_missing_required_field_raises(self):
        s = CitySerializer(data={"name": "NoPopulation"})
        self.assertFalse(s.is_valid())
        self.assertIn("population", s.errors)

    def test_wrong_type_raises(self):
        s = CitySerializer(data={"name": "BadPop", "population": "not-a-number"})
        self.assertFalse(s.is_valid())
        self.assertIn("population", s.errors)

    def test_null_embedded_field_accepted(self):
        data = {"name": "Nowhere", "capital": None, "cities": None, "languages": None}
        s = CountrySerializer(data=data)
        self.assertTrue(s.is_valid(), s.errors)
        self.assertIsNone(s.validated_data.capital)


class EmbeddedModelSerializerNotSavableTests(SimpleTestCase):
    def test_create_raises(self):
        s = CitySerializer()
        with self.assertRaises(NotImplementedError):
            s.create({})

    def test_update_raises(self):
        s = CitySerializer()
        with self.assertRaises(NotImplementedError):
            s.update(City(), {})


class EmbeddedModelSerializerMetaValidationTests(SimpleTestCase):
    def test_missing_meta_raises(self):
        class BrokenSerializer(EmbeddedModelSerializer):
            pass

        with self.assertRaises(AssertionError):
            BrokenSerializer().get_fields()

    def test_missing_meta_model_raises(self):
        class BrokenSerializer(EmbeddedModelSerializer):
            class Meta:
                fields = "__all__"

        with self.assertRaises(AssertionError):
            BrokenSerializer().get_fields()

    def test_missing_meta_fields_raises(self):
        class BrokenSerializer(EmbeddedModelSerializer):
            class Meta:
                model = City

        with self.assertRaises(AssertionError):
            BrokenSerializer().get_fields()

    def test_unknown_field_name_raises(self):
        class BrokenSerializer(EmbeddedModelSerializer):
            class Meta:
                model = City
                fields = ["name", "nonexistent_field"]

        with self.assertRaises(FieldDoesNotExist):
            BrokenSerializer().get_fields()

    def test_explicit_primary_key_raises(self):
        class BrokenSerializer(EmbeddedModelSerializer):
            class Meta:
                model = City
                fields = ["id", "name"]

        with self.assertRaises(ValueError, msg="Primary key field 'id'"):
            BrokenSerializer().get_fields()


class UniqueValidatorStrippingTests(SimpleTestCase):
    """UniqueValidator must be removed for EmbeddedModel fields (manager cannot be queried)."""

    def test_unique_field_is_valid_without_crash(self):
        class UniqueCodeSerializer(EmbeddedModelSerializer):
            class Meta:
                model = CityWithUniqueCode
                fields = "__all__"

        s = UniqueCodeSerializer(data={"name": "NYC", "code": "NYC"})
        # Would raise NotSupportedError before the fix if UniqueValidator was not stripped.
        self.assertTrue(s.is_valid(), s.errors)

    def test_unique_field_has_no_unique_validator(self):
        class UniqueCodeSerializer(EmbeddedModelSerializer):
            class Meta:
                model = CityWithUniqueCode
                fields = "__all__"

        fields = UniqueCodeSerializer().get_fields()
        code_validators = fields["code"].validators
        self.assertFalse(
            any(isinstance(v, UniqueValidator) for v in code_validators),
            "UniqueValidator must not be present on EmbeddedModel fields.",
        )


class ChoicesCoercionTests(SimpleTestCase):
    def test_choices_field_becomes_choice_field(self):
        fields = StatusTagSerializer().get_fields()
        self.assertIsInstance(fields["status"], serializers.ChoiceField)

    def test_choices_field_rejects_invalid_value(self):
        s = StatusTagSerializer(data={"label": "test", "status": 99})
        self.assertFalse(s.is_valid())
        self.assertIn("status", s.errors)

    def test_choices_field_accepts_valid_value(self):
        s = StatusTagSerializer(data={"label": "active", "status": 1})
        self.assertTrue(s.is_valid(), s.errors)
        self.assertEqual(s.validated_data.status, 1)

    def test_choices_field_on_mongo_serializer(self):
        class HolderSerializer(MongoModelSerializer):
            class Meta:
                model = Continent  # has no choices — just confirm no crash
                fields = "__all__"

        # A MongoModelSerializer auto-generating a StatusTag embedded field should
        # also coerce choices. Test via a wrapping model using EmbeddedModelSerializer.
        fields = StatusTagSerializer().get_fields()
        self.assertIsInstance(fields["status"], serializers.ChoiceField)
        self.assertEqual(
            dict(fields["status"].choices),
            {1: "Active", 2: "Inactive"},
        )


class DeclaredFieldOverrideTests(SimpleTestCase):
    def test_declared_field_overrides_auto_generated(self):
        class CityWithFloatPop(EmbeddedModelSerializer):
            population = serializers.FloatField()

            class Meta:
                model = City
                fields = "__all__"

        fields = CityWithFloatPop().get_fields()
        self.assertIsInstance(fields["population"], serializers.FloatField)

    def test_declared_field_is_used_in_serialization(self):
        class CityUpperName(EmbeddedModelSerializer):
            name = serializers.SerializerMethodField()

            def get_name(self, obj):
                return obj.name.upper()

            class Meta:
                model = City
                fields = "__all__"

        city = City(name="paris", population=2_000_000)
        data = CityUpperName(city).data
        self.assertEqual(data["name"], "PARIS")

    def test_declared_field_used_in_deserialization(self):
        class CityWithFloatPop(EmbeddedModelSerializer):
            population = serializers.FloatField()

            class Meta:
                model = City
                fields = "__all__"

        s = CityWithFloatPop(data={"name": "Berlin", "population": "1.5e6"})
        self.assertTrue(s.is_valid(), s.errors)
        self.assertIsInstance(s.validated_data.population, float)
