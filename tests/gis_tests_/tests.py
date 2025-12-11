from django.contrib.gis.geos import LineString, Point, Polygon
from django.contrib.gis.measure import Distance
from django.db import NotSupportedError
from django.db.models import Case, CharField, Value, When
from django.test import TestCase, skipUnlessDBFeature

from .models import City, Zipcode


@skipUnlessDBFeature("gis_enabled")
class LookupTests(TestCase):
    fixtures = ["initial"]

    def test_contains(self):
        qs = City.objects.filter(point__contains=Point(-95.363151, 29.763374)).values_list(
            "name", flat=True
        )
        self.assertCountEqual(qs, ["Houston"])

    def test_contains_errors_on_non_point(self):
        qs = City.objects.filter(point__contains=LineString((0, 0), (1, 1)))
        message = "MongoDB does not support contains on non-Point query geometries."
        with self.assertRaisesMessage(NotSupportedError, message):
            qs.first()

    def test_disjoint(self):
        qs = City.objects.filter(point__disjoint=Point(100, 50)).values_list("name", flat=True)
        self.assertIn("Houston", qs)

    def test_distance_gt(self):
        houston = City.objects.get(name="Houston")
        expected = ["Oklahoma City", "Wellington", "Pueblo", "Lawrence", "Chicago", "Victoria"]
        qs = City.objects.filter(point__distance_gt=(houston.point, 362826)).values_list(
            "name", flat=True
        )
        self.assertCountEqual(qs, expected)

    def test_distance_gte(self):
        houston = City.objects.get(name="Houston")
        expected = [
            "Dallas",
            "Oklahoma City",
            "Wellington",
            "Pueblo",
            "Lawrence",
            "Chicago",
            "Victoria",
        ]
        qs = City.objects.filter(point__distance_gte=(houston.point, 362825)).values_list(
            "name", flat=True
        )
        self.assertCountEqual(qs, expected)

    def test_distance_lt(self):
        houston = City.objects.get(name="Houston")
        qs = City.objects.filter(point__distance_lt=(houston.point, 362825))
        self.assertCountEqual(qs, [houston])

    def test_distance_lte(self):
        houston = City.objects.get(name="Houston")
        qs = City.objects.filter(point__distance_lte=(houston.point, 362826)).values_list(
            "name", flat=True
        )
        self.assertCountEqual(qs, ["Houston", "Dallas"])  # Dallas is roughly ~363 km from Houston

    def test_distance_units(self):
        chicago = City.objects.get(name="Chicago")
        qs = City.objects.filter(point__distance_lt=(chicago.point, Distance(km=720))).values_list(
            "name", flat=True
        )
        self.assertCountEqual(qs, ["Lawrence", "Chicago"])
        qs = City.objects.filter(point__distance_lt=(chicago.point, Distance(mi=447))).values_list(
            "name", flat=True
        )
        self.assertCountEqual(qs, ["Lawrence", "Chicago"])

    def test_dwithin(self):
        houston = City.objects.get(name="Houston")
        expected = ["Houston", "Dallas", "Pueblo", "Oklahoma City", "Lawrence"]
        qs = City.objects.filter(point__dwithin=(houston.point, 0.2)).values_list("name", flat=True)
        self.assertCountEqual(qs, expected)

    def test_dwithin_unsupported_units(self):
        qs = City.objects.filter(point__dwithin=(Point(40.7670, -73.9820), Distance(km=1)))
        message = "Only numeric values of radian units are allowed on geodetic distance queries."
        with self.assertRaisesMessage(ValueError, message):
            qs.first()

    def test_intersects(self):
        city = City.objects.create(point=Point(95, 30))
        qs = City.objects.filter(point__intersects=Point(95, 30).buffer(10))
        self.assertCountEqual(qs, [city])

    def test_within(self):
        zipcode = Zipcode.objects.get(code="77002")
        qs = City.objects.filter(point__within=zipcode.poly).values_list("name", flat=True)
        self.assertCountEqual(qs, ["Houston"])

    def test_unsupported(self):
        msg = "MongoDB does not support the 'same_as' lookup."
        with self.assertRaisesMessage(NotSupportedError, msg):
            City.objects.get(point__same_as=Point(95, 30))

    def test_unsupported_expr(self):
        downtown_area = Polygon(
            (
                (-122.4194, 37.7749),
                (-122.4194, 37.8049),
                (-122.3894, 37.8049),
                (-122.3894, 37.7749),
                (-122.4194, 37.7749),
            )
        )

        qs = City.objects.annotate(
            area_type=Case(
                When(point__within=downtown_area, then=Value("Downtown")),
                default=Value("Other"),
                output_field=CharField(),
            )
        )

        message = "MongoDB does not support GIS lookups as expressions."
        with self.assertRaisesMessage(NotSupportedError, message):
            qs.first()
