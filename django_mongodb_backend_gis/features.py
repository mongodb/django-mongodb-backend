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
                # SRIDs aren't supported.
                "gis_tests.geogapp.tests.GeographyTest.test05_geography_layermapping",
                "gis_tests.geoapp.tests.GeoModelTest.test_proxy",
                # 'WithinLookup' object has no attribute 'as_mql'
                # "gis_tests.relatedapp.tests.RelatedGeoModelTest.test10_combine",
                # GEOSException: Calling transform() with no SRID set is not supported
                "gis_tests.relatedapp.tests.RelatedGeoModelTest.test06_f_expressions",
                # 'Adapter' object has no attribute 'srid'
                "gis_tests.geoapp.test_expressions.GeoExpressionsTests.test_geometry_value_annotation",
                # To triage:
                "gis_tests.geoapp.test_expressions.GeoExpressionsTests.test_multiple_annotation",
                # 'ContainsLookup' object has no attribute 'as_mql'.
                "gis_tests.geoapp.test_regress.GeoRegressionTests.test_empty_count",
                "gis_tests.geoapp.tests.GeoLookupTest.test_contains_contained_lookups",
                # Object of type ObjectId is not JSON serializable
                "gis_tests.geoapp.test_serializers.GeoJSONSerializerTests.test_fields_option",
                # LinearRing requires at least 4 points, got 1.
                "gis_tests.geoapp.test_serializers.GeoJSONSerializerTests.test_geometry_field_option",
                "gis_tests.geoapp.tests.GeoLookupTest.test_null_geometries",
                # source and target must be of type SpatialReference
                "gis_tests.geoapp.test_serializers.GeoJSONSerializerTests.test_id_field_option",
                "gis_tests.geoapp.test_serializers.GeoJSONSerializerTests.test_serialization_base",
                "gis_tests.geoapp.test_serializers.GeoJSONSerializerTests.test_srid_option",
                # 'DisjointLookup' object has no attribute 'as_mql'
                "gis_tests.geoapp.tests.GeoLookupTest.test_disjoint_lookup",
                # 'SameAsLookup' object has no attribute 'as_mql'
                "gis_tests.geoapp.tests.GeoLookupTest.test_equals_lookups",
                # 'WithinLookup' object has no attribute 'as_mql'
                "gis_tests.geoapp.tests.GeoLookupTest.test_subquery_annotation",
                "gis_tests.geoapp.tests.GeoQuerySetTest.test_within_subquery",
                # issubclass() arg 1 must be a class
                "gis_tests.geoapp.tests.GeoModelTest.test_geometryfield",
                # KeyError: 'within' connection.ops.gis_operators[self.lookup_name]
                "gis_tests.geoapp.tests.GeoModelTest.test_gis_query_as_string",
                # Point object != Point object
                "gis_tests.geoapp.test_expressions.GeoExpressionsTests.test_update_from_other_field",
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
