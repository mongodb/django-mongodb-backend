import unittest

try:
    import rest_framework  # noqa: F401
except ImportError:
    raise unittest.SkipTest("djangorestframework not installed") from None

from django.core.exceptions import FieldDoesNotExist
from django.db import models
from django.test import SimpleTestCase
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from django_mongodb_backend.rest_framework import (
    EmbeddedModelSerializer,
    MongoModelSerializer,
    PolymorphicEmbeddedModelSerializer,
)

from .models import (
    Cat,
    City,
    CityWithUniqueCode,
    Continent,
    Country,
    Dog,
    PetOwner,
    StatusTag,
)

# ---------------------------------------------------------------------------
# Manually declared serializers (user-defined style)
# ---------------------------------------------------------------------------


class CitySerializer(EmbeddedModelSerializer):
    class Meta:
        model = City
        fields = "__all__"


class CountrySerializer(EmbeddedModelSerializer):
    class Meta:
        model = Country
        fields = "__all__"


class ContinentSerializer(MongoModelSerializer):
    class Meta:
        model = Continent
        fields = "__all__"


# ---------------------------------------------------------------------------
# EmbeddedModelSerializer tests
# ---------------------------------------------------------------------------


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


class EmbeddedModelSerializerRoundTripTests(SimpleTestCase):
    def test_roundtrip(self):
        original = City(name="Oslo", population=700_000)
        serialized = CitySerializer(original).data
        reconstructed_serializer = CitySerializer(data=dict(serialized))
        self.assertTrue(reconstructed_serializer.is_valid(), reconstructed_serializer.errors)
        result = reconstructed_serializer.validated_data
        self.assertEqual(result.name, original.name)
        self.assertEqual(result.population, original.population)

    def test_nested_roundtrip(self):
        capital = City(name="Vienna", population=1_900_000)
        original = Country(name="Austria", capital=capital, cities=None, languages=["German"])
        serialized = CountrySerializer(original).data
        reconstructed_serializer = CountrySerializer(data=dict(serialized))
        self.assertTrue(reconstructed_serializer.is_valid(), reconstructed_serializer.errors)
        result = reconstructed_serializer.validated_data
        self.assertEqual(result.name, original.name)
        self.assertEqual(result.capital.name, capital.name)
        self.assertEqual(result.languages, ["German"])


class EmbeddedModelSerializerNotSavableTests(SimpleTestCase):
    def test_create_raises(self):
        s = CitySerializer()
        with self.assertRaises(NotImplementedError):
            s.create({})

    def test_update_raises(self):
        s = CitySerializer()
        with self.assertRaises(NotImplementedError):
            s.update(City(), {})


# ---------------------------------------------------------------------------
# MongoModelSerializer tests
# ---------------------------------------------------------------------------


class MongoModelSerializerAutoFieldTests(SimpleTestCase):
    def test_embedded_field_is_serializer(self):
        fields = ContinentSerializer().get_fields()
        self.assertIsInstance(fields["country"], EmbeddedModelSerializer)

    def test_embedded_array_field_is_list_serializer(self):
        fields = ContinentSerializer().get_fields()
        self.assertIsInstance(fields["countries"], serializers.ListSerializer)
        self.assertIsInstance(fields["countries"].child, EmbeddedModelSerializer)

    def test_array_field_is_list_field(self):
        fields = ContinentSerializer().get_fields()
        self.assertIsInstance(fields["notable_cities"], serializers.ListField)

    def test_name_is_char_field(self):
        fields = ContinentSerializer().get_fields()
        self.assertIsInstance(fields["name"], serializers.CharField)


class MongoModelSerializerToRepresentationTests(SimpleTestCase):
    def _make_continent(self):
        capital = City(name="Amsterdam", population=900_000)
        country = Country(
            name="Netherlands",
            capital=capital,
            cities=[City(name="Rotterdam", population=650_000)],
            languages=["Dutch"],
        )
        return Continent(
            name="Europe",
            country=country,
            countries=[country],
            notable_cities=["Amsterdam"],
        )

    def test_embedded_field(self):
        continent = self._make_continent()
        data = ContinentSerializer(continent).data
        self.assertEqual(data["country"]["name"], "Netherlands")
        self.assertEqual(data["country"]["capital"]["name"], "Amsterdam")

    def test_embedded_array_field(self):
        continent = self._make_continent()
        data = ContinentSerializer(continent).data
        self.assertEqual(len(data["countries"]), 1)
        self.assertEqual(data["countries"][0]["name"], "Netherlands")

    def test_array_field(self):
        continent = self._make_continent()
        data = ContinentSerializer(continent).data
        self.assertEqual(data["notable_cities"], ["Amsterdam"])

    def test_null_values(self):
        continent = Continent(name="Antarctica", country=None, countries=None, notable_cities=None)
        data = ContinentSerializer(continent).data
        self.assertIsNone(data["country"])
        self.assertIsNone(data["countries"])
        self.assertIsNone(data["notable_cities"])


class MongoModelSerializerToInternalValueTests(SimpleTestCase):
    def test_embedded_field(self):
        data = {
            "name": "Oceania",
            "country": {
                "name": "Australia",
                "capital": {"name": "Canberra", "population": 450_000},
                "cities": None,
                "languages": ["English"],
            },
            "countries": None,
            "notable_cities": None,
        }
        s = ContinentSerializer(data=data)
        self.assertTrue(s.is_valid(), s.errors)
        validated = s.validated_data
        self.assertIsInstance(validated["country"], Country)
        self.assertIsInstance(validated["country"].capital, City)
        self.assertEqual(validated["country"].capital.name, "Canberra")

    def test_embedded_array_field(self):
        data = {
            "name": "Africa",
            "country": None,
            "countries": [
                {
                    "name": "Nigeria",
                    "capital": {"name": "Abuja", "population": 3_600_000},
                    "cities": None,
                    "languages": ["English"],
                }
            ],
            "notable_cities": None,
        }
        s = ContinentSerializer(data=data)
        self.assertTrue(s.is_valid(), s.errors)
        validated = s.validated_data
        self.assertIsInstance(validated["countries"][0], Country)

    def test_null_embedded_field(self):
        data = {
            "name": "Atlantis",
            "country": None,
            "countries": None,
            "notable_cities": None,
        }
        s = ContinentSerializer(data=data)
        self.assertTrue(s.is_valid(), s.errors)
        self.assertIsNone(s.validated_data["country"])

    def test_array_field(self):
        data = {
            "name": "Asia",
            "country": None,
            "countries": None,
            "notable_cities": ["Tokyo", "Beijing"],
        }
        s = ContinentSerializer(data=data)
        self.assertTrue(s.is_valid(), s.errors)
        self.assertEqual(s.validated_data["notable_cities"], ["Tokyo", "Beijing"])


class MongoModelSerializerExplicitFieldTests(SimpleTestCase):
    """Explicit field declarations override auto-generation."""

    def test_explicit_embedded_field(self):
        class CustomContinentSerializer(MongoModelSerializer):
            country = CitySerializer()  # Wrong type on purpose — override check

            class Meta:
                model = Continent
                fields = ["name", "country"]

        fields = CustomContinentSerializer().get_fields()
        self.assertIsInstance(fields["country"], CitySerializer)

    def test_partial(self):
        class PartialContinentSerializer(MongoModelSerializer):
            class Meta:
                model = Continent
                fields = ["name"]

        fields = PartialContinentSerializer().get_fields()
        self.assertIn("name", fields)
        self.assertNotIn("country", fields)
        self.assertNotIn("countries", fields)


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


# ---------------------------------------------------------------------------
# PolymorphicEmbeddedModelSerializer tests
# ---------------------------------------------------------------------------


class PetOwnerSerializer(MongoModelSerializer):
    class Meta:
        model = PetOwner
        fields = "__all__"


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


# ---------------------------------------------------------------------------
# Choices coercion tests (fix: _get_serializer_field must coerce to ChoiceField)
# ---------------------------------------------------------------------------


class StatusTagSerializer(EmbeddedModelSerializer):
    class Meta:
        model = StatusTag
        fields = "__all__"


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


# ---------------------------------------------------------------------------
# Declared field override tests (fix: get_fields must merge _declared_fields)
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Field mapping propagation tests (fix: custom serializer_field_mapping must
# propagate into auto-generated EmbeddedModelSerializer instances)
# ---------------------------------------------------------------------------


class FieldMappingPropagationTests(SimpleTestCase):
    def _make_custom_serializer(self):
        """MongoModelSerializer subclass that maps IntegerField → FloatField."""

        class CustomContinentSerializer(MongoModelSerializer):
            serializer_field_mapping = {
                **MongoModelSerializer.serializer_field_mapping,
                models.IntegerField: serializers.FloatField,
            }

            class Meta:
                model = Continent
                fields = "__all__"

        return CustomContinentSerializer

    def test_custom_mapping_applies_to_direct_embedded_field(self):
        # Country.capital is EmbeddedModelField(City); City.population is IntegerField.
        # The custom mapping should make population a FloatField inside Country.
        cls = self._make_custom_serializer()
        country_serializer = cls().get_fields()["country"]
        city_serializer = country_serializer.get_fields()["capital"]
        self.assertIsInstance(city_serializer.get_fields()["population"], serializers.FloatField)

    def test_custom_mapping_applies_to_embedded_array_field(self):
        # Country.cities is EmbeddedModelArrayField(City); City.population is IntegerField.
        cls = self._make_custom_serializer()
        country_serializer = cls().get_fields()["country"]
        cities_list_serializer = country_serializer.get_fields()["cities"]
        city_fields = cities_list_serializer.child.get_fields()
        self.assertIsInstance(city_fields["population"], serializers.FloatField)

    def test_default_mapping_unchanged_for_base_serializer(self):
        # Verify the base ContinentSerializer still uses IntegerField for City.population.
        base_fields = ContinentSerializer().get_fields()
        capital_fields = base_fields["country"].get_fields()["capital"].get_fields()
        self.assertIsInstance(capital_fields["population"], serializers.IntegerField)
