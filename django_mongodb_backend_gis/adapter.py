import collections


class Adapter(collections.UserDict):
    def __init__(self, obj, geography=False):
        """
        Initialize on the spatial object.
        """
        self.data = {
            "type": obj.__class__.__name__,
            "coordinates": obj.coords,
        }
