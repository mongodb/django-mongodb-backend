=========
GeoDjango
=========

.. versionadded:: 5.2.0b2

Django MongoDB Backend supports :doc:`GeoDjango<django:ref/contrib/gis/index>`.

Configuration
=============

#. Install the necessary :doc:`Geospatial libraries
   <django:ref/contrib/gis/install/geolibs>` (GEOS and GDAL).
#. Add :mod:`django.contrib.gis` to :setting:`INSTALLED_APPS` in your settings.
   This is so that the ``gis`` templates can be located -- if not done, then
   features such as the geographic admin or KML sitemaps will not function properly.

Limitations
===========

- MongoDB doesn't support any spatial reference system identifiers
  (:attr:`BaseSpatialField.srid <django.contrib.gis.db.models.BaseSpatialField.srid>`)
  besides 4326 (WGS84) .
- None of the :doc:`GIS QuerySet APIs <django:ref/contrib/gis/geoquerysets>` (lookups,
  aggregates, and database functions) are supported.
- :class:`~django.contrib.gis.db.models.RasterField` isn't supported.
