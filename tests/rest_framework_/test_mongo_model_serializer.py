import unittest

try:
    import rest_framework  # noqa: F401
except ImportError:
    raise unittest.SkipTest("djangorestframework not installed") from None

from django.db import models
from django.test import SimpleTestCase
from rest_framework import serializers

from django_mongodb_backend.rest_framework import EmbeddedModelSerializer, MongoModelSerializer

from .models import City, Continent, Country


class CitySerializer(EmbeddedModelSerializer):
    class Meta:
        model = City
        fields = "__all__"


class ContinentSerializer(MongoModelSerializer):
    class Meta:
        model = Continent
        fields = "__all__"


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
