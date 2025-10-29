================
Encrypted fields
================

.. versionadded:: 5.2.3

Django MongoDB Backend supports :doc:`manual:core/queryable-encryption`.

See :doc:`/howto/queryable-encryption` for more information on how to use
Queryable Encryption with Django MongoDB Backend.

See the :doc:`/topics/queryable-encryption` topic guide for
more information on developing applications with Queryable Encryption.

The following Django fields are supported by Django MongoDB Backend for use with
Queryable Encryption.

+----------------------------------------+------------------------------------------------------+
| Encrypted Field                        | Django Field                                         |
+========================================+======================================================+
| ``EncryptedBigIntegerField``           | :class:`~django.db.models.BigIntegerField`           |
+----------------------------------------+------------------------------------------------------+
| ``EncryptedBinaryField``               | :class:`~django.db.models.BinaryField`               |
+----------------------------------------+------------------------------------------------------+
| ``EncryptedBooleanField``              | :class:`~django.db.models.BooleanField`              |
+----------------------------------------+------------------------------------------------------+
| ``EncryptedCharField``                 | :class:`~django.db.models.CharField`                 |
+----------------------------------------+------------------------------------------------------+
| ``EncryptedDateField``                 | :class:`~django.db.models.DateField`                 |
+----------------------------------------+------------------------------------------------------+
| ``EncryptedDateTimeField``             | :class:`~django.db.models.DateTimeField`             |
+----------------------------------------+------------------------------------------------------+
| ``EncryptedDecimalField``              | :class:`~django.db.models.DecimalField`              |
+----------------------------------------+------------------------------------------------------+
| ``EncryptedDurationField``             | :class:`~django.db.models.DurationField`             |
+----------------------------------------+------------------------------------------------------+
| ``EncryptedFloatField``                | :class:`~django.db.models.FloatField`                |
+----------------------------------------+------------------------------------------------------+
| ``EncryptedGenericIPAddressField``     | :class:`~django.db.models.GenericIPAddressField`     |
+----------------------------------------+------------------------------------------------------+
| ``EncryptedIntegerField``              | :class:`~django.db.models.IntegerField`              |
+----------------------------------------+------------------------------------------------------+
| ``EncryptedPositiveIntegerField``      | :class:`~django.db.models.PositiveIntegerField`      |
+----------------------------------------+------------------------------------------------------+
| ``EncryptedPositiveBigIntegerField``   | :class:`~django.db.models.PositiveBigIntegerField`   |
+----------------------------------------+------------------------------------------------------+
| ``EncryptedPositiveSmallIntegerField`` | :class:`~django.db.models.PositiveSmallIntegerField` |
+----------------------------------------+------------------------------------------------------+
| ``EncryptedSmallIntegerField``         | :class:`~django.db.models.SmallIntegerField`         |
+----------------------------------------+------------------------------------------------------+
| ``EncryptedTextField``                 | :class:`~django.db.models.TextField`                 |
+----------------------------------------+------------------------------------------------------+
| ``EncryptedTimeField``                 | :class:`~django.db.models.TimeField`                 |
+----------------------------------------+------------------------------------------------------+
| ``EncryptedURLField``                  | :class:`~django.db.models.URLField`                  |
+----------------------------------------+------------------------------------------------------+
| ``EncryptedUUIDField``                 | :class:`~django.db.models.UUIDField`                 |
+----------------------------------------+------------------------------------------------------+

The following MongoDB-specific fields are supported by Django MongoDB Backend
for use with Queryable Encryption.

+----------------------------------------+------------------------------------------------------+
| Encrypted Field                        | MongoDB Field                                        |
+----------------------------------------+------------------------------------------------------+
| ``EncryptedArrayField``                | :class:`~.fields.ArrayField`                         |
+----------------------------------------+------------------------------------------------------+
| ``EncryptedEmbeddedModelArrayField``   | :class:`~.fields.EmbeddedModelArrayField`            |
+----------------------------------------+------------------------------------------------------+
| ``EncryptedEmbeddedModelField``        | :class:`~.fields.EmbeddedModelField`                 |
+----------------------------------------+------------------------------------------------------+
| ``EncryptedObjectIdField``             | :class:`~.fields.ObjectIdField`                      |
+----------------------------------------+------------------------------------------------------+

These fields don't support the ``queries`` argument::
- ``EncryptedArrayField``
- ``EncryptedEmbeddedModelArrayField``
- ``EncryptedEmbeddedModelField``

The following fields are supported by Django MongoDB Backend but not supported
by Queryable Encryption.

+--------------------------------------+--------------------------------------------------------------------------------------------------------------------+
| Field                                | Limitation                                                                                                         |
+--------------------------------------+--------------------------------------------------------------------------------------------------------------------+
| :class:`~django.db.models.SlugField` | :ref:`Queryable Encryption does not support TTL Indexes or Unique Indexes <manual:qe-reference-encryption-limits>` |
+--------------------------------------+--------------------------------------------------------------------------------------------------------------------+

Limitations
===========

MongoDB imposes some restrictions on encrypted fields:

* They cannot be indexed.
* They cannot be part of a unique constraint.
* They cannot be null.

``EncryptedFieldMixin``
=======================

.. class:: EncryptedFieldMixin

    .. versionadded:: 5.2.3

    A mixin that can be used to create custom encrypted fields with Queryable
    Encryption.

    To create an encrypted field, inherit from ``EncryptedFieldMixin`` and
    your custom field class:

    .. code-block:: python

        from django.db import models
        from django_mongodb_backend.fields import EncryptedFieldMixin
        from myapp.fields import MyField


        class MyEncryptedField(EncryptedFieldMixin, MyField):
            pass


    You can then use your custom encrypted field in a model, specifying the
    desired query types:

    .. code-block:: python

        class MyModel(models.Model):
            my_encrypted_field = MyEncryptedField(
                queries={"queryType": "equality"},
            )
            my_encrypted_field_too = MyEncryptedField(
                queries={"queryType": "range"},
            )
