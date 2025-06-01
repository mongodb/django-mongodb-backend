from django.contrib.gis.db.backends.base.features import BaseSpatialFeatures
from django.utils.functional import cached_property

from django_mongodb_backend.features import DatabaseFeatures as MongoFeatures


class DatabaseFeatures(BaseSpatialFeatures, MongoFeatures):
    has_spatialrefsys_table = False
    supports_transform = False

    @cached_property
    def django_test_expected_failures(self):
        expected_failures = super().django_test_expected_failures
        expected_failures.update(
            {
                # SRIDs aren't populated: AssertionError: 4326 != None
                # self.assertEqual(4326, nullcity.point.srid)
                "gis_tests.geoapp.tests.GeoModelTest.test_proxy",
                # MongoDB does not support the within lookup
                "gis_tests.relatedapp.tests.RelatedGeoModelTest.test06_f_expressions",
                # 'Adapter' object has no attribute 'srid'
                "gis_tests.geoapp.test_expressions.GeoExpressionsTests.test_geometry_value_annotation",
                # Object of type ObjectId is not JSON serializable
                "gis_tests.geoapp.test_serializers.GeoJSONSerializerTests.test_fields_option",
                "gis_tests.geoapp.test_serializers.GeoJSONSerializerTests.test_geometry_field_option",
                "gis_tests.geoapp.test_serializers.GeoJSONSerializerTests.test_serialization_base",
                "gis_tests.geoapp.test_serializers.GeoJSONSerializerTests.test_srid_option",
                # KeyError: 'within' connection.ops.gis_operators[self.lookup_name]
                "gis_tests.geoapp.tests.GeoModelTest.test_gis_query_as_string",
                # No lookups are supported (yet?)
                "gis_tests.geoapp.tests.GeoLookupTest.test_gis_lookups_with_complex_expressions",
            }
        )
        return expected_failures

    @cached_property
    def django_test_skips(self):
        skips = super().django_test_skips
        skips.update(
            {
                "inspectdb not supported.": {
                    "gis_tests.inspectapp.tests.InspectDbTests",
                },
                "Raw SQL not supported": {
                    "gis_tests.geoapp.tests.GeoModelTest.test_raw_sql_query",
                },
            },
        )
        return skips
