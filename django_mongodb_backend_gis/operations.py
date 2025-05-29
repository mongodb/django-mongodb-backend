from django.contrib.gis import geos
from django.contrib.gis.db import models
from django.contrib.gis.db.backends.base.operations import BaseSpatialOperations

from django_mongodb_backend.operations import (
    DatabaseOperations as MongoOperations,
)

from .adapter import Adapter


class DatabaseOperations(BaseSpatialOperations, MongoOperations):
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
        def converter(value, expression, connection):  # noqa: ARG001
            if value is None:
                return None
            geom_class = getattr(geos, value["type"])
            if issubclass(geom_class, geos.GeometryCollection):
                # TODO: confirm this is correct.
                return geom_class(
                    [
                        geom_class._allowed(value["coordinates"][x][0])
                        for x in range(len(value["coordinates"]))
                    ],
                    srid=4326,
                )
            return geom_class(value["coordinates"], srid=4326)

        return converter
