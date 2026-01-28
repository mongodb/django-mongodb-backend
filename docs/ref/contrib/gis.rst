=========
GeoDjango
=========

Django MongoDB Backend supports :doc:`GeoDjango<django:ref/contrib/gis/index>`.

Spatial fields
==============

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

.. _spatial-lookups:

Spatial lookups
===============

.. versionadded:: 6.0.1

The following :ref:`spatial lookups <django:spatial-lookups>` are supported:

- :lookup:`contains <gis-contains>` (the lookup geometry must be a
  :class:`~django.contrib.gis.geos.Point`)
- :lookup:`disjoint`
- :lookup:`distance_gt`
- :lookup:`distance_lte`
- :lookup:`dwithin`
- :lookup:`intersects`
- :lookup:`within`

For all lookups, the lookup value must be a :ref:`geometry object
<django:ref/contrib/gis/geos:Geometry Objects>` (e.g.
:class:`~django.contrib.gis.geos.Point`,
:class:`~django.contrib.gis.geos.LineString`, etc.) or a :ref:`geometry
collection <django:ref/contrib/gis/geos:Geometry Collections>` (e.g.
:class:`~django.contrib.gis.geos.MultiPoint`,
:class:`~django.contrib.gis.geos.MultiLineString`, etc.). MongoDB does not
support expressions (:class:`~django.db.models.F`,
:class:`~django.db.models.Subquery`, etc.) for spatial lookup values.

Raw spatial queries
===================

You can use any of the :ref:`geospatial query operators
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
- :ref:`GIS aggregate functions <gis-aggregation-functions>` and
  :doc:`geographic database functions <django:ref/contrib/gis/functions>`
  aren't supported.
- :class:`~django.contrib.gis.db.models.RasterField` isn't supported.
