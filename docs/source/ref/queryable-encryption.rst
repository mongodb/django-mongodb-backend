====================
Queryable Encryption
====================

.. versionadded:: 5.2.0b2

Django MongoDB Backend supports Queryable Encryption for MongoDB.

Each model field stores encrypted data in the database.

.. _encrypted-fields:

Encrypted fields
================

Encrypted fields are subclasses of Django's built-in fields and can be used to
store sensitive data with MongoDB's :doc:`Queryable Encryption
<queryable-encryption>` feature. They are subclasses of Django's built-in fields
before storing it in the database.

+----------------------------------------+------------------------------------------------------+
| Encrypted Field                        | Django Field                                         |
+========================================+======================================================+
| ``EncryptedBigIntegerField``           | :class:`~django.db.models.BigIntegerField`           |
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
| ``EncryptedPositiveBigIntegerField``   | :class:`~django.db.models.PositiveBigIntegerField`   |
+----------------------------------------+------------------------------------------------------+
| ``EncryptedPositiveIntegerField``      | :class:`~django.db.models.PositiveIntegerField`      |
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

``EncryptedFieldMixin``
=======================

.. class:: EncryptedFieldMixin

   A mixin that can be used to create custom encrypted fields
   that support MongoDB's Queryable Encryption.

You can use the ``EncryptedFieldMixin`` to create your own encrypted fields. This mixin
supports the use of a ``queries`` argument in the field definition to specify query type
for the field::

    from django.db import models
    from django_mongodb_backend.fields import EncryptedFieldMixin
    from .models import MyField


    class MyEncryptedField(EncryptedFieldMixin, MyField):
        pass


    class MyModel(models.Model):
        my_encrypted_field = MyEncryptedField(
            queries={"queryType": "equality"},
            # Other field options...
        )

Unsupported fields
==================

The following fields are supported by Django MongoDB Backend but are not
supported by Queryable Encryption.

+--------------------------------------+------------------------------------------------------------+
| :class:`~django.db.models.SlugField` | Queryable Encryption does not :doc:`support unique indexes |
|                                      | on encrypted fields                                        |
|                                      | <manual:core/queryable-encryption/reference/limitations>`. |
+--------------------------------------+------------------------------------------------------------+
