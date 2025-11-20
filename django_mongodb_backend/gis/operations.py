from django.contrib.gis import geos
from django.contrib.gis.db import models
from django.contrib.gis.db.backends.base.operations import BaseSpatialOperations
from django.contrib.gis.measure import Distance
from django.db import NotSupportedError
from django.db.backends.base.operations import BaseDatabaseOperations

from .adapter import Adapter
from .utils import SpatialOperator


def _gis_within_operator(field, value, op=None, params=None):  # noqa: ARG001
    return {
        field: {
            "$geoWithin": {
                "$geometry": {
                    "type": value["type"],
                    "coordinates": value["coordinates"],
                }
            }
        }
    }


def _gis_intersects_operator(field, value, op=None, params=None):  # noqa: ARG001
    return {
        field: {
            "$geoIntersects": {
                "$geometry": {
                    "type": value["type"],
                    "coordinates": value["coordinates"],
                }
            }
        }
    }


def _gis_disjoint_operator(field, value, op=None, params=None):  # noqa: ARG001
    return {
        field: {
            "$not": {
                "$geoIntersects": {
                    "$geometry": {
                        "type": value["type"],
                        "coordinates": value["coordinates"],
                    }
                }
            }
        }
    }


def _gis_contains_operator(field, value, op=None, params=None):  # noqa: ARG001
    value_type = value["type"]
    if value_type != "Point":
        raise NotSupportedError("MongoDB does not support contains on non-Point query geometries.")
    return {
        field: {
            "$geoIntersects": {
                "$geometry": {
                    "type": value_type,
                    "coordinates": value["coordinates"],
                }
            }
        }
    }


def _gis_distance_operator(field, value, op=None, params=None):
    distance = params[0].m if hasattr(params[0], "m") else params[0]
    if op == "distance_gt" or op == "distance_gte":
        cmd = {
            field: {
                "$not": {
                    "$geoWithin": {
                        "$centerSphere": [
                            value["coordinates"],
                            distance / 6378100,  # radius of earth in meters
                        ],
                    }
                }
            }
        }
    else:
        cmd = {
            field: {
                "$geoWithin": {
                    "$centerSphere": [
                        value["coordinates"],
                        distance / 6378100,  # radius of earth in meters
                    ],
                }
            }
        }
    return cmd


def _gis_dwithin_operator(field, value, op=None, params=None):  # noqa: ARG001
    return {field: {"$geoWithin": {"$centerSphere": [value["coordinates"], params[0]]}}}


class GISOperations(BaseSpatialOperations, BaseDatabaseOperations):
    Adapter = Adapter

    disallowed_aggregates = (
        models.Collect,
        models.Extent,
        models.Extent3D,
        models.MakeLine,
        models.Union,
    )

    @property
    def gis_operators(self):
        return {
            "contains": SpatialOperator("contains", _gis_contains_operator),
            "intersects": SpatialOperator("intersects", _gis_intersects_operator),
            "disjoint": SpatialOperator("disjoint", _gis_disjoint_operator),
            "within": SpatialOperator("within", _gis_within_operator),
            "distance_gt": SpatialOperator("distance_gt", _gis_distance_operator),
            "distance_gte": SpatialOperator("distance_gte", _gis_distance_operator),
            "distance_lt": SpatialOperator("distance_lt", _gis_distance_operator),
            "distance_lte": SpatialOperator("distance_lte", _gis_distance_operator),
            "dwithin": SpatialOperator("dwithin", _gis_dwithin_operator),
        }

    unsupported_functions = {
        "Area",
        "AsGeoJSON",
        "AsGML",
        "AsKML",
        "AsSVG",
        "AsWKB",
        "AsWKT",
        "Azimuth",
        "BoundingCircle",
        "Centroid",
        "ClosestPoint",
        "Difference",
        "Distance",
        "Envelope",
        "ForcePolygonCW",
        "FromWKB",
        "FromWKT",
        "GeoHash",
        "GeometryDistance",
        "Intersection",
        "IsEmpty",
        "IsValid",
        "Length",
        "LineLocatePoint",
        "MakeValid",
        "MemSize",
        "NumGeometries",
        "NumPoints",
        "Perimeter",
        "PointOnSurface",
        "Reverse",
        "Scale",
        "SnapToGrid",
        "SymDifference",
        "Transform",
        "Translate",
        "Union",
    }

    def geo_db_type(self, f):
        return "object"

    def get_geometry_converter(self, expression):
        srid = expression.output_field.srid

        def converter(value, expression, connection):  # noqa: ARG001
            if value is None:
                return None

            geom_class = getattr(geos, value["type"])
            if geom_class.__name__ == "GeometryCollection":
                return geom_class(
                    [
                        getattr(geos, v["type"])(*v["coordinates"], srid=srid)
                        for v in value["geometries"]
                    ],
                    srid=srid,
                )
            if issubclass(geom_class, geos.GeometryCollection):
                sub_geom_class = geom_class._allowed
                # MultiLineString allows both LineString and LinearRing but should be
                # initialized with LineString.
                if isinstance(sub_geom_class, tuple):
                    sub_geom_class = sub_geom_class[0]
                return geom_class(
                    [
                        sub_geom_class(*value["coordinates"][x])
                        for x in range(len(value["coordinates"]))
                    ],
                    srid=srid,
                )
            return geom_class(*value["coordinates"], srid=srid)

        return converter

    def get_distance(self, f, value, lookup_type):
        value = value[0]
        if isinstance(value, Distance):
            if f.geodetic(self.connection):
                raise ValueError(
                    "Only numeric values of degree units are allowed on geodetic distance queries."
                )
            dist_param = getattr(value, Distance.unit_attname(f.units_name(self.connection)))
        else:
            dist_param = value
        return [dist_param]
