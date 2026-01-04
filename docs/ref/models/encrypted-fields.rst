================
Encrypted fields
================

.. currentmodule:: django_mongodb_backend.fields

.. versionadded:: 6.0.1

To use encrypted fields, you must :doc:`configure Queryable Encryption
</howto/queryable-encryption>`.

The following tables detail which fields have encrypted counterparts. In all
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
    :class:`~django.db.models.FileField`, No - the use case for encrypting this field is unclear.
    :class:`~django.db.models.FilePathField`, No - the use case for encrypting this field is unclear.
    :class:`~django.db.models.FloatField`, Yes
    :class:`~django.db.models.GenericIPAddressField`, Yes
    :class:`~django.db.models.ImageField`, No - the use case for encrypting this field is unclear.
    :class:`~django.db.models.IntegerField`, Yes
    :class:`~django.db.models.JSONField`, No - ``JSONField`` isn't recommended.
    :class:`~django.db.models.PositiveIntegerField`, Yes
    :class:`~django.db.models.PositiveBigIntegerField`, Yes
    :class:`~django.db.models.PositiveSmallIntegerField`, Yes
    :class:`~django.db.models.SlugField`, No - it requires a unique index which Queryable Encryption doesn't support.
    :class:`~django.db.models.SmallIntegerField`, Yes
    :class:`~django.db.models.TextField`, Yes
    :class:`~django.db.models.TimeField`, Yes
    :class:`~django.db.models.URLField`, Yes
    :class:`~django.db.models.UUIDField`, Yes

.. csv-table:: ``django_mongodb_backend.fields``
   :header: "Model Field", "Encrypted version available?"

    :class:`ArrayField`, Yes
    :class:`EmbeddedModelArrayField`, Yes
    :class:`EmbeddedModelField`, Yes
    :class:`ObjectIdField`, Yes
    :class:`PolymorphicEmbeddedModelField`, No - it may be implemented in the
    future.
    :class:`PolymorphicEmbeddedModelArrayField`, No - it may be implemented in the future.

.. _encrypted-fields-queries:

``EncryptedField.queries``
--------------------------

Most encrypted fields take an optional ``queries`` argument. It's a dictionary
that specifies the type of queries that can be performed on the field, as well
as any query options.

The :ref:`available query types <manual:qe-fundamentals-encrypt-query>` depend
on your version of MongoDB. For example, in MongoDB 8.0, the supported types
are ``equality`` and ``range``.

The supported lookups for ``equality`` queries are: :lookup:`exact` and
lookup:`in`. The supported operators are AND (``&``) and OR (``|``).

The supported lookups for ``range`` queries include those of ``equality``
queries as well as :lookup:`lt`, :lookup:`lte`, :lookup:`gt`, and
:lookup:`gte`.

These fields don't support the ``queries`` argument:

- ``EncryptedArrayField``
- ``EncryptedEmbeddedModelArrayField``
- ``EncryptedEmbeddedModelField``

Embedded model encryption
=========================

There are two ways to encrypt embedded models. You can either encrypt the
entire subdocument, in which case you can't query any the subdocuments fields,
or you can encrypt only selected fields of the subdocument.

Encrypting the entire subdocument
---------------------------------

To encrypt a subdocument, use ``EncryptedEmbeddedModelField`` or
``EncryptedEmbeddedModelArrayField``. In this case, the field's embedded model
cannot have any encrypted fields.

Encrypting selected fields of a subdocument
-------------------------------------------

To encrypt only select fields of a subdocument, use :class:`EmbeddedModelField`
and any of the other encrypted fields on the embedded model.

MongoDB doesn't support encrypting selected fields of
``EmbeddedModelArrayField``.

Limitations
===========

MongoDB imposes some restrictions on encrypted fields:

* They cannot be indexed.
* They cannot be part of a unique constraint.
* They cannot be null.

``QuerySet`` limitations
------------------------

In addition to :ref:`Django MongoDB Backend's QuerySet limitations
<known-issues-limitations-querying>`, some ``QuerySet`` methods aren't
supported on encrypted fields. Each unsupported method is followed by a sample
error message from the database. Depending on the exact query, error messages
may vary.

- :meth:`~django.db.models.query.QuerySet.order_by`: Cannot add an encrypted
  field as a prefix of another encrypted field.
- :meth:`~django.db.models.query.QuerySet.alias`,
  :meth:`~django.db.models.query.QuerySet.annotate`,
  :meth:`~django.db.models.query.QuerySet.distinct`: Cannot group on field
  '<encrypted_field>' which is encrypted with the random algorithm or whose
  encryption properties are not known until runtime.
- :meth:`~django.db.models.query.QuerySet.dates`,
  :meth:`~django.db.models.query.QuerySet.datetimes`: If the value type is a
  date, the type of the index must also be date (and vice versa).
- :meth:`~django.db.models.query.QuerySet.in_bulk`: Encrypted fields can't have
  unique constraints.
- Queries that join multiple collections and require the ``let`` operator. Such
  queries usually involve expressions or subqueries: Non-empty 'let' field is
  not allowed in the $lookup aggregation stage over an encrypted collection.

There are also several ``QuerySet`` methods that aren't permitted on any models
(regardless of whether or not they have encrypted fields) that use a database
connection with Automatic Encryption. Each unsupported method is followed by a
sample error message from the database.

- :meth:`~django.db.models.query.QuerySet.update`: Multi-document updates are
  not allowed with Queryable Encryption.
- :meth:`~django.db.models.query.QuerySet.aggregate`: Invalid reference to an
  encrypted field within aggregate expression.
- :meth:`~django.db.models.query.QuerySet.union`: Aggregation stage $unionWith
  is not allowed or supported with automatic encryption.

``EncryptedFieldMixin``
=======================

.. class:: EncryptedFieldMixin

    .. versionadded:: 6.0.1

    Use this mixin to create encrypted versions of your own custom fields. For
    example, to create an encrypted version of ``MyField``::

        from django.db import models
        from django_mongodb_backend.fields import EncryptedFieldMixin
        from myapp.fields import MyField


        class MyEncryptedField(EncryptedFieldMixin, MyField):
            pass

    This adds the :ref:`queries <encrypted-fields-queries>` argument to the
    field.
