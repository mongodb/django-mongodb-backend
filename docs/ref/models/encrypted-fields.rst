================
Encrypted fields
================

.. versionadded:: 5.2.2

Django MongoDB Backend supports :doc:`manual:core/queryable-encryption`.

See :doc:`/howto/queryable-encryption` for more information on how to use
Queryable Encryption with Django MongoDB Backend.

See the :doc:`Queryable Encryption topic </topics/queryable-encryption>` for
more information on developing applications with Queryable Encryption.

The following fields are supported by Django MongoDB Backend for use with
Queryable Encryption.

+----------------------------------------+------------------------------------------------------+
| Encrypted Field                        | Django Field                                         |
+========================================+======================================================+
| ``EncryptedBooleanField``              | :class:`~django.db.models.BooleanField`              |
+----------------------------------------+------------------------------------------------------+
| ``EncryptedBigIntegerField``           | :class:`~django.db.models.BigIntegerField`           |
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

The following fields are supported by Django MongoDB Backend but are not
supported by Queryable Encryption.

+--------------------------------------+-----------------------------------------------+
| :class:`~django.db.models.SlugField` | Indexes aren't supported on encrypted fields. |
+--------------------------------------+-----------------------------------------------+

``EncryptedFieldMixin``
=======================

.. class:: EncryptedFieldMixin

    .. versionadded:: 5.2.2

    A mixin that can be used to create custom encrypted fields that support
    MongoDB's Queryable Encryption.

    To create a custom encrypted field, inherit from ``EncryptedFieldMixin`` and
    the desired Django field class.


    For example, to create a custom encrypted field that supports ``equality``
    queries, you can define it as follows:

    .. code-block:: python

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
