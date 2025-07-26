from django.core.exceptions import ImproperlyConfigured

try:
    from .lookups import register_lookups
except ImproperlyConfigured:
    # GIS libraries not installed
    pass
else:
    register_lookups()
