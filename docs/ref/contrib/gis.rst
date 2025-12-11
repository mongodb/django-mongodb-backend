=========
GeoDjango
=========

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

The following :doc:`GIS QuerySet APIs <django:ref/contrib/gis/geoquerysets>` are supported:
- :meth:`~django.contrib.gis.db.models.query.GeoQuerySet.contains`
- :meth:`~django.contrib.gis.db.models.query.GeoQuerySet.intersects`
- :meth:`~django.contrib.gis.db.models.query.GeoQuerySet.disjoint`
- :meth:`~django.contrib.gis.db.models.query.GeoQuerySet.within`
- :meth:`~django.contrib.gis.db.models.query.GeoQuerySet.distance_gt`
- :meth:`~django.contrib.gis.db.models.query.GeoQuerySet.distance_gte`
- :meth:`~django.contrib.gis.db.models.query.GeoQuerySet.distance_lt`
- :meth:`~django.contrib.gis.db.models.query.GeoQuerySet.distance_lte`
- :meth:`~django.contrib.gis.db.models.query.GeoQuerySet.dwithin`

You can also use any of the :ref:`geospatial query operators
<manual:geospatial-query-operators>` or the :ref:`geospatial aggregation
pipeline stage <geospatial-aggregation>` in :meth:`.raw_aggregate` queries.

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
- QuerySet APIs do not support subqueries or expressions.
- :class:`~django.contrib.gis.db.models.RasterField` isn't supported.
