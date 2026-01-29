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
