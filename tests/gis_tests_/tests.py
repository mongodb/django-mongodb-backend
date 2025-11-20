from django.contrib.gis.geos import Point
from django.db import NotSupportedError
from django.test import TestCase, skipUnlessDBFeature

from .models import City


@skipUnlessDBFeature("gis_enabled")
class LookupTests(TestCase):
    def test_unsupported_lookups(self):
        msg = "MongoDB does not support the 'same_as' lookup."
        with self.assertRaisesMessage(NotSupportedError, msg):
            City.objects.get(point__same_as=Point(95, 30))

    def test_within_lookup(self):
        city = City.objects.create(point=Point(95, 30))
        qs = City.objects.filter(point__within=Point(95, 30).buffer(10))
        self.assertIn(city, qs)

    def test_intersects_lookup(self):
        city = City.objects.create(point=Point(95, 30))
        qs = City.objects.filter(point__intersects=Point(95, 30).buffer(10))
        self.assertIn(city, qs)

    def test_disjoint_lookup(self):
        city = City.objects.create(point=Point(50, 30))
        qs = City.objects.filter(point__disjoint=Point(100, 50))
        self.assertIn(city, qs)

    def test_contains_lookup(self):
        city = City.objects.create(point=Point(95, 30))
        qs = City.objects.filter(point__contains=Point(95, 30))
        self.assertIn(city, qs)

    def test_distance_gt_lookup(self):
        city = City.objects.create(point=Point(95, 30))
        qs = City.objects.filter(point__distance_gt=(Point(0, 0), 100))
        self.assertIn(city, qs)

    def test_distance_lt_lookup(self):
        city = City.objects.create(point=Point(40.7589, -73.9851))
        qs = City.objects.filter(point__distance_lt=(Point(40.7670, -73.9820), 1000))
        self.assertIn(city, qs)

    def test_distance_gte_lookup(self):
        city = City.objects.create(point=Point(95, 30))
        qs = City.objects.filter(point__distance_gt=(Point(0, 0), 100))
        self.assertIn(city, qs)

    def test_distance_lte_lookup(self):
        city = City.objects.create(point=Point(40.7589, -73.9851))
        qs = City.objects.filter(point__distance_lt=(Point(40.7670, -73.9820), 1000))
        self.assertIn(city, qs)

    def test_dwithin_lookup(self):
        city = City.objects.create(point=Point(40.7589, -73.9851))
        qs = City.objects.filter(point__dwithin=(Point(40.7670, -73.9820), 1000))
        self.assertIn(city, qs)
