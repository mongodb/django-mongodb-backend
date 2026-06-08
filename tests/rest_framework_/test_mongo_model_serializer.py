import unittest

try:
    import rest_framework  # noqa: F401
except ImportError:
    raise unittest.SkipTest("djangorestframework not installed") from None

from django.db import models
from django.test import SimpleTestCase, TestCase
from rest_framework import serializers

from django_mongodb_backend.rest_framework import EmbeddedModelSerializer, MongoModelSerializer

from .models import City, Continent, Country
from .serializers import CitySerializer, ContinentSerializer


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


class MongoModelSerializerCreateTests(TestCase):
    def test_create_with_embedded_field(self):
        data = {
            "name": "Europe",
            "country": {
                "name": "Germany",
                "capital": {"name": "Berlin", "population": 3_500_000},
                "cities": None,
                "languages": None,
            },
            "countries": None,
            "notable_cities": None,
        }
        s = ContinentSerializer(data=data)
        self.assertTrue(s.is_valid(), s.errors)
        continent = s.save()

        loaded = Continent.objects.get(pk=continent.pk)
        self.assertEqual(loaded.name, "Europe")
        self.assertIsInstance(loaded.country, Country)
        self.assertEqual(loaded.country.name, "Germany")
        self.assertIsInstance(loaded.country.capital, City)
        self.assertEqual(loaded.country.capital.name, "Berlin")

    def test_create_with_embedded_array_field(self):
        data = {
            "name": "South America",
            "country": None,
            "countries": [
                {
                    "name": "Brazil",
                    "capital": {"name": "Brasília", "population": 3_000_000},
                    "cities": None,
                    "languages": ["Portuguese"],
                },
                {
                    "name": "Argentina",
                    "capital": {"name": "Buenos Aires", "population": 3_100_000},
                    "cities": None,
                    "languages": ["Spanish"],
                },
            ],
            "notable_cities": None,
        }
        s = ContinentSerializer(data=data)
        self.assertTrue(s.is_valid(), s.errors)
        continent = s.save()

        loaded = Continent.objects.get(pk=continent.pk)
        self.assertEqual(len(loaded.countries), 2)
        self.assertIsInstance(loaded.countries[0], Country)
        self.assertEqual(loaded.countries[0].name, "Brazil")
        self.assertEqual(loaded.countries[1].name, "Argentina")

    def test_create_with_array_field(self):
        data = {
            "name": "Asia",
            "country": None,
            "countries": None,
            "notable_cities": ["Tokyo", "Beijing", "Mumbai"],
        }
        s = ContinentSerializer(data=data)
        self.assertTrue(s.is_valid(), s.errors)
        continent = s.save()

        loaded = Continent.objects.get(pk=continent.pk)
        self.assertEqual(loaded.notable_cities, ["Tokyo", "Beijing", "Mumbai"])

    def test_create_with_null_fields(self):
        data = {"name": "Antarctica", "country": None, "countries": None, "notable_cities": None}
        s = ContinentSerializer(data=data)
        self.assertTrue(s.is_valid(), s.errors)
        continent = s.save()

        loaded = Continent.objects.get(pk=continent.pk)
        self.assertIsNone(loaded.country)
        self.assertIsNone(loaded.countries)
        self.assertIsNone(loaded.notable_cities)


class MongoModelSerializerUpdateTests(TestCase):
    def setUp(self):
        capital = City(name="Paris", population=2_000_000)
        country = Country(name="France", capital=capital, cities=None, languages=["French"])
        self.continent = Continent.objects.create(
            name="Europe", country=country, countries=None, notable_cities=["Paris"]
        )

    def test_update_scalar_field(self):
        s = ContinentSerializer(
            self.continent,
            data={
                "name": "Europa",
                "country": {
                    "name": "France",
                    "capital": {"name": "Paris", "population": 2_000_000},
                    "cities": None,
                    "languages": ["French"],
                },
                "countries": None,
                "notable_cities": ["Paris"],
            },
        )
        self.assertTrue(s.is_valid(), s.errors)
        s.save()

        loaded = Continent.objects.get(pk=self.continent.pk)
        self.assertEqual(loaded.name, "Europa")
        self.assertEqual(loaded.country.name, "France")

    def test_update_embedded_field(self):
        s = ContinentSerializer(
            self.continent,
            data={
                "name": "Europe",
                "country": {
                    "name": "Germany",
                    "capital": {"name": "Berlin", "population": 3_500_000},
                    "cities": None,
                    "languages": ["German"],
                },
                "countries": None,
                "notable_cities": ["Paris"],
            },
        )
        self.assertTrue(s.is_valid(), s.errors)
        s.save()

        loaded = Continent.objects.get(pk=self.continent.pk)
        self.assertEqual(loaded.country.name, "Germany")
        self.assertEqual(loaded.country.capital.name, "Berlin")

    def test_update_to_null_embedded_field(self):
        s = ContinentSerializer(
            self.continent,
            data={
                "name": "Europe",
                "country": None,
                "countries": None,
                "notable_cities": None,
            },
        )
        self.assertTrue(s.is_valid(), s.errors)
        s.save()

        loaded = Continent.objects.get(pk=self.continent.pk)
        self.assertIsNone(loaded.country)


class MongoModelSerializerRoundTripTests(TestCase):
    def test_serialize_from_db_then_create(self):
        capital = City(name="Rome", population=2_800_000)
        cities = [City(name="Milan", population=1_300_000)]
        country = Country(name="Italy", capital=capital, cities=cities, languages=["Italian"])
        original = Continent.objects.create(
            name="Europe",
            country=country,
            countries=[country],
            notable_cities=["Rome", "Milan"],
        )

        # Serialize a DB-loaded instance; id is read-only so passing it back is safe.
        data = dict(ContinentSerializer(Continent.objects.get(pk=original.pk)).data)
        s = ContinentSerializer(data=data)
        self.assertTrue(s.is_valid(), s.errors)
        copy = s.save()

        self.assertNotEqual(copy.pk, original.pk)
        loaded = Continent.objects.get(pk=copy.pk)
        self.assertEqual(loaded.name, "Europe")
        self.assertEqual(loaded.country.name, "Italy")
        self.assertEqual(loaded.country.capital.name, "Rome")
        self.assertEqual(loaded.countries[0].cities[0].name, "Milan")
        self.assertEqual(loaded.notable_cities, ["Rome", "Milan"])
