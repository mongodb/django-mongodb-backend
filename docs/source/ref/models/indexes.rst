=====================
Model index reference
=====================

.. module:: django_mongodb_backend.indexes
   :synopsis: Database indexes for MongoDB.

Some MongoDB-specific indexes are available in
``django_mongodb_backend.indexes``.

``SearchIndex``
===============

.. class:: SearchIndex(fields=(), name=None)

Creates a basic :doc:`search index <atlas:atlas-search/index-definitions>` on
the given field(s).

If ``name`` isn't provided, one will be generated automatically. If you need
to reference the name in your search query and don't provide your own name,
you can lookup the generated one using: ``Model._meta.indexes[0].name``
(substiting a different index as needed if your model has multiple indexes).

``VectorSearchIndex``
=====================

.. class:: VectorSearchIndex(fields=(), similarities="cosine", name=None)

A subclass of :class:`SearchIndex` that creates a :doc:`vector search index
<atlas:atlas-vector-search/vector-search-type>` on the given field(s).

Available values for ``similarities`` are ``"euclidean"``, ``"cosine"``, and
``"dotProduct"``. You can provide either a string value, in which case that
value will be applied to all fields, or a list or tuple of values of the same
length as list/tuple of fields with a similarity value for each field.

<document restrictions on arrayfield, etc.>
