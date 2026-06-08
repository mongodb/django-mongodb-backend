import unittest

try:
    import rest_framework  # noqa: F401
except ImportError:
    raise unittest.SkipTest("djangorestframework not installed") from None

from django.test import TestCase

from .models import City, Continent, Country
from .serializers import ContinentSerializer


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
