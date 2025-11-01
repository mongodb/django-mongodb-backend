================
Encrypted fields
================

.. versionadded:: 5.2.3

Django MongoDB Backend supports :doc:`manual:core/queryable-encryption`.

See :doc:`/howto/queryable-encryption` for more information on how to use
Queryable Encryption with Django MongoDB Backend.

See the :doc:`/topics/queryable-encryption` topic guide for
more information on developing applications with Queryable Encryption.

The following tables detailed which fields have encrypted counterparts. In all
cases, the encrypted field names are simply prefixed with ``Encrypted``, e.g.
``EncryptedCharField``. They are importable from
``django_mongodb_backend.fields``.

.. csv-table:: ``django.db.models``
   :header: "Model Field", "Encrypted version available?"

    :class:`~django.db.models.BigIntegerField`, Yes
    :class:`~django.db.models.BinaryField`, Yes
    :class:`~django.db.models.BooleanField`, Yes
    :class:`~django.db.models.CharField`, Yes
    :class:`~django.db.models.DateField`, Yes
    :class:`~django.db.models.DateTimeField`, Yes
    :class:`~django.db.models.DecimalField`, Yes
    :class:`~django.db.models.DurationField`, Yes
    :class:`~django.db.models.EmailField`, Yes
    :class:`~django.db.models.FileField`, No: the use case for encrypting this field is unclear.
    :class:`~django.db.models.FilePathField`, No: the use case for encrypting this field is unclear.
    :class:`~django.db.models.GenericIPAddressField`, Yes
    :class:`~django.db.models.ImageField`, No: the use case for encrypting this field is unclear.
    :class:`~django.db.models.IntegerField`, Yes
    :class:`~django.db.models.JSONField`, No: ``JSONField`` isn't recommended.
    :class:`~django.db.models.PositiveIntegerField`, Yes
    :class:`~django.db.models.PositiveBigIntegerField`, Yes
    :class:`~django.db.models.PositiveSmallIntegerField`, Yes
    :class:`~django.db.models.SlugField`, No: it requires a unique index which Queryable Encryption doesn't support.
    :class:`~django.db.models.SmallIntegerField`, Yes
    :class:`~django.db.models.TimeField`, Yes
    :class:`~django.db.models.TextField`, Yes
    :class:`~django.db.models.URLField`, Yes
    :class:`~django.db.models.UUIDField`, Yes

.. csv-table:: ``django_mongodb_backend.fields``
   :header: "Model Field", "Encrypted version available?"

    :class:`~.fields.ArrayField`, Yes
    :class:`~.fields.EmbeddedModelArrayField`, Yes
    :class:`~.fields.EmbeddedModelField`, Yes
    :class:`~.fields.ObjectIdField`, Yes
    :class:`~.fields.PolymorphicEmbeddedModelField`, No: may be implemented in the future.
    :class:`~.fields.PolymorphicEmbeddedModelArrayField`, No: may be implemented in the future.

These fields don't support the ``queries`` argument:

- ``EncryptedArrayField``
- ``EncryptedEmbeddedModelArrayField``
- ``EncryptedEmbeddedModelField``

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
