from django.contrib.gis.db.backends.base.features import BaseSpatialFeatures
from django.utils.functional import cached_property


class GISFeatures(BaseSpatialFeatures):
    has_spatialrefsys_table = False
    supports_transform = False

    @cached_property
    def django_test_expected_failures(self):
        expected_failures = super().django_test_expected_failures
        expected_failures.update(
            {
                # annotate with Value not supported, e.g.
                # QuerySet.annotate(p=Value(p, GeometryField(srid=4326)
                "gis_tests.geoapp.test_expressions.GeoExpressionsTests.test_geometry_value_annotation",
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
                "MongoDB doesn't support the SRID used in this test.": {
                    # Error messages:
                    # - Can't extract geo keys
                    # - Longitude/latitude is out of bounds
                    "gis_tests.geoapp.test_expressions.GeoExpressionsTests.test_update_from_other_field",
                    "gis_tests.layermap.tests.LayerMapTest.test_encoded_name",
                    "gis_tests.relatedapp.tests.RelatedGeoModelTest.test06_f_expressions",
                    # SouthTexasCity fixture objects use SRID 2278 which is ignored
                    # by the patched version of loaddata in the Django fork.
                    "gis_tests.distapp.tests.DistanceTest.test_init",
                },
                "ImproperlyConfigured isn't raised when using RasterField": {
                    # Normally RasterField.db_type() raises an error, but MongoDB
                    # migrations don't need to call it, so the check doesn't happen.
                    "gis_tests.gis_migrations.test_operations.NoRasterSupportTests",
                },
                "MongoDB doesn't support redundant spatial indexes.": {
                    # Error: Index already exists with a different name
                    "gis_tests.geoapp.test_indexes.SchemaIndexesTests.test_index_name",
                },
                "GIS lookups not supported.": {
                    "gis_tests.geoapp.tests.GeoModelTest.test_gis_query_as_string",
                    "gis_tests.geoapp.tests.GeoLookupTest.test_gis_lookups_with_complex_expressions",
                },
                "GeoJSONSerializer doesn't support ObjectId.": {
                    "gis_tests.geoapp.test_serializers.GeoJSONSerializerTests.test_fields_option",
                    "gis_tests.geoapp.test_serializers.GeoJSONSerializerTests.test_geometry_field_option",
                    "gis_tests.geoapp.test_serializers.GeoJSONSerializerTests.test_serialization_base",
                    "gis_tests.geoapp.test_serializers.GeoJSONSerializerTests.test_srid_option",
                },
            },
        )
        return skips
