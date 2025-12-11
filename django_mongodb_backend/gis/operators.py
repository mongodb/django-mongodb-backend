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
                "MongoDB does not support contains on non-Point query geometries."
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


class DistanceBase(Operator):
    name = "distance_base"

    def as_mql(self, field, value, params=None):
        distance = params[0].m if hasattr(params[0], "m") else params[0]
        if self.name == "distance_gt" or self.name == "distance_gte":
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


class DistanceGT(DistanceBase):
    name = "distance_gt"


class DistanceGTE(DistanceBase):
    name = "distance_gte"


class DistanceLT(DistanceBase):
    name = "distance_lt"


class DistanceLTE(DistanceBase):
    name = "distance_lte"


class DWithin(Operator):
    name = "dwithin"

    def as_mql(self, field, value, params=None):
        return {field: {"$geoWithin": {"$centerSphere": [value["coordinates"], params[0]]}}}


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
