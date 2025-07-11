from django.contrib.gis.db.models.lookups import GISLookup
from django.db import NotSupportedError


def gis_lookup(self, compiler, connection):  # noqa: ARG001
    raise NotSupportedError(f"MongoDB does not support the {self.lookup_name} lookup.")


def register_lookups():
    GISLookup.as_mql = gis_lookup
