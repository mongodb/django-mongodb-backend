from math import radians

from django.db import NotSupportedError


class Operator:
    def as_sql(self, connection, lookup, template_params, sql_params):
        # Return some dummy value to prevent str(queryset.query) from crashing.
        # The output of as_sql() is meaningless for this no-SQL backend.
        return self.name, []


class Contains(Operator):
    name = "contains"

    def as_mql(self, field, value, params=None):
        value_type = value["type"]
        if value_type != "Point":
            raise NotSupportedError(
                "MongoDB does not support contains on non-Point lookup geometries."
            )
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


class Disjoint(Operator):
    name = "disjoint"

    def as_mql(self, field, value, params=None):
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


class DistanceLTE(Operator):
    name = "distance_lte"

    def get_geo_within(self, value, params):
        distance = params[0]
        # Get the distance in meters if it's a Distance object.
        distance = distance.m if hasattr(distance, "m") else distance
        return {
            "$geoWithin": {
                "$centerSphere": [
                    value["coordinates"],
                    distance / 6378100,  # radius of earth in meters
                ],
            }
        }

    def as_mql(self, field, value, params=None):
        return {field: self.get_geo_within(value, params)}


class DistanceGT(DistanceLTE):
    name = "distance_gt"

    def as_mql(self, field, value, params=None):
        return {field: {"$not": self.get_geo_within(value, params)}}


class DWithin(Operator):
    name = "dwithin"

    def as_mql(self, field, value, params=None):
        # The parameter is always in degrees. GISOperations.get_distance()
        # prohibits using Distance objects since MongoDB doesn't support any
        # projected systems.
        param = radians(params[0])
        return {field: {"$geoWithin": {"$centerSphere": [value["coordinates"], param]}}}


class Intersects(Operator):
    name = "intersects"

    def as_mql(self, field, value, params=None):
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


class Within(Operator):
    name = "within"

    def as_mql(self, field, value, params=None):
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
