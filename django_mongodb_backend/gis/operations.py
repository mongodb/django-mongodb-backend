from django.contrib.gis import geos
from django.contrib.gis.db import models
from django.contrib.gis.db.backends.base.operations import BaseSpatialOperations

from .adapter import Adapter


class GISOperations(BaseSpatialOperations):
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
        return {}

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
