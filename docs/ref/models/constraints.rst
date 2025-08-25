==========================
Model constraint reference
==========================

.. _unique-constraints:

Unique constraints
==================

By default, model field unique constraints - whether created with
:attr:`Field.unique <django.db.models.Field.unique>`,
:attr:`Meta.unique_together <django.db.models.Options.unique_together>` or
:class:`~django.db.models.UniqueConstraint` - treat ``NULL`` values as distinct
from each other. That is, you can store multiple documents a ``NULL`` value.
This is consistent with most SQL databases.

If you wish to only allow one document with a ``NULL`` value, use a
:class:`~django.db.models.UniqueConstraint` with
:attr:`~django.db.models.UniqueConstraint.nulls_distinct` set to ``False``.

.. versionadded:: 6.0.2

    Support for :attr:`UniqueConstraint.nulls_distinct
    <django.db.models.UniqueConstraint.nulls_distinct>` was added.

MongoDB-specific constraints
============================

.. module:: django_mongodb_backend.constraints
   :synopsis: Database constraints for MongoDB.

Some MongoDB-specific :doc:`constraints <django:ref/models/constraints>`, for
use on a model's :attr:`Meta.constraints<django.db.models.Options.constraints>`
option, are available in ``django_mongodb_backend.constraints``.

Embedded field constraints
==========================

``EmbeddedFieldConstraint``
---------------------------

.. class:: EmbeddedFieldUniqueConstraint(**kwargs)

    .. versionadded:: 6.0.2

    Subclass of :class:`~django.db.models.UniqueConstraint` for use on a
    top-level model in order to add a unique constraint on subfields of
    :class:`~.fields.EmbeddedModelField` and
    :class:`~.fields.EmbeddedModelArrayField`.

    The ``fields`` argument uses dotted paths to reference embedded fields. For
    examples, see :ref:`embedded-model-field-unique-constraints` and
    :ref:`embedded-model-array-field-unique-constraints`.
