=============
System checks
=============

This page catalogs the :doc:`system checks <django:ref/checks>` in Django
MongoDB Backend.

Constraints
===========

* **mongodb.constraints.embedded_unique.E001**:
  :class:`.EmbeddedFieldUniqueConstraint` ``<name>`` must have
  ``nulls_distinct=False`` since it references
  :class:`~django_mongodb_backend.fields.EmbeddedModelArrayField` ``<name>``.

Indexes
=======

* **mongodb.indexes.search.W001**: This MongoDB server does
  not support :class:`.SearchIndex`. The index won't be created. Use an
  Atlas-enabled version of MongoDB, or silence this warning if you don't care
  about it.
* **mongodb.indexes.search.E002**:
  :class:`.VectorSearchIndex` requires ``size`` on field ``<field>``.
* **mongodb.indexes.search.E003**:
  :class:`.VectorSearchIndex` requires the base field of ``ArrayField``
  ``<field>`` to be FloatField or IntegerField but is ``<field_type>``.
* **mongodb.indexes.search.E004**:
  :class:`.VectorSearchIndex` does not support field  ``<field>``
  (``<field type>``). Allowed types are boolean, date, number, objectId,
  string, uuid.
* **mongodb.indexes.search.E005**:
  :class:`.VectorSearchIndex` requires the same number of similarities and
  vector fields; ``<model>`` has  ``<#>`` ``ArrayField``\(s) but similarities
  has ``<#>``  element(s).
* **mongodb.indexes.search.E006**:
  :class:`.VectorSearchIndex` requires at least one :class:`.ArrayField` to
  store vector data. If you want to perform search operations without vectors,
  use :class:`.SearchIndex` instead.

Fields
======

* **mongodb.fields.array.E001**: Base field for array has errors: ...
* **mongodb.fields.array.E002**: Base field for array cannot be a
  related field.
* **mongodb.fields.array.E003**: :class:`.ArrayField` cannot have both
  ``size`` and ``max_size``.
* **mongodb.fields.array.W004**: Base field for array has warnings: ...
* **mongodb.fields.auto.E001**: MongoDB does not support
  :class:`~django.db.models.AutoField`. Use
  :class:`django_mongodb_backend.fields.ObjectIdAutoField` instead.
* **mongodb.fields.embedded_model.E001**: Embedded models cannot have
  relational fields.
* **mongodb.fields.embedded_model.E002**: Embedded models must be a
  subclass of :class:`django_mongodb_backend.models.EmbeddedModel`.
* **mongodb.fields.embedded_model.W003**: Embedded models ``<model A>`` and
  ``<model B>`` both have field ``<field>`` of different type. It may be
  impossible to query both fields.
* **mongodb.fields.embedded_model.W004**: Using ``db_index=True`` on embedded
  fields is deprecated in favor of using :class:`.EmbeddedFieldIndex` in
  ``Meta.indexes`` on the top-level model.
* **mongodb.fields.embedded_model.W005**: Using ``unique=True`` on embedded
  fields is deprecated in favor of using :class:`.EmbeddedFieldUniqueConstraint`
  in ``Meta.constraints`` on the top-level model.
* **mongodb.fields.embedded_model.W006**: Using ``Meta.constraints`` on
  embedded models is deprecated in favor of using
  :class:`.EmbeddedFieldUniqueConstraint` in ``Meta.constraints`` on the
  top-level model.
* **mongodb.fields.embedded_model.W007**: Using ``Meta.indexes`` on embedded
  models is deprecated in favor of using :class:`.EmbeddedFieldIndex` in
  ``Meta.indexes`` on the top-level model.
* **mongodb.fields.embedded_model.W008**: Using ``Meta.unique_together`` on
  embedded models is deprecated in favor of using
  :class:`.EmbeddedFieldUniqueConstraint` in ``Meta.constraints`` on the
  top-level model.
* **mongodb.fields.encryption.E001**: ``<field>`` cannot contain
  encrypted fields (found ``<field class>``).
