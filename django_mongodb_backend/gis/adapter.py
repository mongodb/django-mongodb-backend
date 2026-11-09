import collections


class Adapter(collections.UserDict):
    srid = 4326

    def __init__(self, obj, geography=False):
        """
        Initialize on the spatial object per
        https://www.mongodb.com/docs/manual/reference/geojson/.
        """
        self.data = self.get_data(obj)

    def get_data(self, obj):
        if obj.__class__.__name__ == "GeometryCollection":
            return {
                "type": obj.__class__.__name__,
                "geometries": [self.get_data(x) for x in obj],
            }
        return {
            "type": obj.__class__.__name__,
            "coordinates": obj.coords,
        }

    @classmethod
    def _fix_polygon(cls, poly):
        return poly
