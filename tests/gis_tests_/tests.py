from django.contrib.gis.geos import Point
from django.db import NotSupportedError
from django.test import TestCase, skipUnlessDBFeature

from .models import City


@skipUnlessDBFeature("gis_enabled")
class LookupTests(TestCase):
    def test_unsupported_lookups(self):
        msg = "MongoDB does not support the same_as lookup."
        with self.assertRaisesMessage(NotSupportedError, msg):
            City.objects.get(point__same_as=Point(95, 30))
