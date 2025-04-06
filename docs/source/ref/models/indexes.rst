=====================
Model index reference
=====================

.. module:: django_mongodb_backend.indexes
   :synopsis: Database indexes for MongoDB.

Some MongoDB-specific indexes are available in
``django_mongodb_backend.indexes``.

``SearchIndex``
===============

.. class:: SearchIndex(*expressions, **kwargs)

...


``VectorSearchIndex``
=====================

.. class:: VectorSearchIndex(*expressions, similarities="cosine", **kwargs)

Available values for ``similarities`` are ``"euclidean"``, ``"cosine"``, and
``"dotProduct"``.

...
