=========
GeoDjango
=========

.. versionadded:: 5.2.0b2

Django MongoDB Backend supports :doc:`GeoDjango<django:ref/contrib/gis/index>`.

Each model field stores data as :doc:`GeoJSON objects
<manual:reference/geojson>`.

* :class:`~django.contrib.gis.db.models.PointField`
* :class:`~django.contrib.gis.db.models.LineStringField`
* :class:`~django.contrib.gis.db.models.PolygonField`
* :class:`~django.contrib.gis.db.models.MultiPointField`
* :class:`~django.contrib.gis.db.models.MultiLineStringField`
* :class:`~django.contrib.gis.db.models.MultiPolygonField`
* :class:`~django.contrib.gis.db.models.GeometryCollectionField`

All fields have a :doc:`2dsphere index
<manual:core/indexes/index-types/geospatial/2dsphere>` created on them.

The :ref:`geospatial aggregation stage <geospatial-operators>` only supports
one operator: :doc:`$geoNear <manual:reference/operator/aggregation/geoNear>`.
You can use it in :meth:`.raw_aggregate` queries.

The :ref:`geospatial query operators <manual:geospatial-query-operators>`
aren't supported.

Configuration
=============

#. Install the necessary :doc:`Geospatial libraries
   <django:ref/contrib/gis/install/geolibs>` (GEOS and GDAL).
#. Add :mod:`django.contrib.gis` to :setting:`INSTALLED_APPS` in your settings.
   This is so that the ``gis`` templates can be located -- if not done, then
   features such as the geographic admin or KML sitemaps will not function
   properly.

Limitations
===========

- MongoDB doesn't support any spatial reference system identifiers
  (:attr:`BaseSpatialField.srid
  <django.contrib.gis.db.models.BaseSpatialField.srid>`)
  besides `4326 (WGS84) <https://spatialreference.org/ref/epsg/4326/>`_.
- None of the :doc:`GIS QuerySet APIs <django:ref/contrib/gis/geoquerysets>`
  (lookups, aggregates, and database functions) are supported.
- :class:`~django.contrib.gis.db.models.RasterField` isn't supported.
