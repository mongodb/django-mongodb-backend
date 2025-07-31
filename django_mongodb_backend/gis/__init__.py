from django.core.exceptions import ImproperlyConfigured

try:
    from .lookups import register_lookups
except ImproperlyConfigured:
    # GIS libraries (GDAL/GEOS) not installed.
    pass
else:
    register_lookups()
