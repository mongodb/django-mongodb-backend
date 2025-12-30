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

The following :ref:`spatial lookups <django:spatial-lookups>` are supported:

- :lookup:`contains <gis-contains>`
- :lookup:`disjoint`
- :lookup:`distance_gt`
- :lookup:`distance_gte`
- :lookup:`distance_lt`
- :lookup:`distance_lte`
- :lookup:`dwithin`
- :lookup:`intersects`
- :lookup:`within`

You can also use any of the :ref:`geospatial query operators
<manual:geospatial-query-operators>` or the :ref:`geospatial aggregation
pipeline stage <geospatial-aggregation>` in :meth:`.raw_aggregate` queries.

.. versionadded:: 6.0.1

    Support for spatial lookups was added.

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
- Spatial lookups don't support subqueries or expressions.
- :ref:`GIS aggregate functions <gis-aggregation-functions>` and
  :doc:`geographic database functions <django:ref/contrib/gis/functions>`
  aren't supported.
- :class:`~django.contrib.gis.db.models.RasterField` isn't supported.
