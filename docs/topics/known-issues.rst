============================
Known issues and limitations
============================

This document summarizes some known issues and limitations of this library.
If you notice an issue not listed, use the :ref:`issue-tracker` to report a bug
or request a feature.

Like any database, MongoDB has some particularities. Also keep in mind that
because MongoDB is a NoSQL database, it's impossible to implement SQL-specific
functionality.

Model fields
============

- :class:`~django.db.models.DateTimeField` is limited to millisecond precision
  (rather than microsecond like most other databases), and correspondingly,
  :class:`~django.db.models.DurationField` stores milliseconds rather than
  microseconds.

- Some of Django's built-in fields aren't supported by MongoDB:

  - :class:`~django.db.models.AutoField` (including
    :class:`~django.db.models.BigAutoField` and
    :class:`~django.db.models.SmallAutoField`)
  - :class:`~django.db.models.CompositePrimaryKey`
  - :class:`~django.db.models.GeneratedField`

Querying
========

- The following ``QuerySet`` methods aren't supported:

  - :meth:`extra() <django.db.models.query.QuerySet.extra>`
  - :meth:`prefetch_related() <django.db.models.query.QuerySet.prefetch_related>`

- :meth:`QuerySet.delete() <django.db.models.query.QuerySet.delete>` and
  :meth:`update() <django.db.models.query.QuerySet.update>` do not support queries
  that span multiple collections.

- When querying :class:`~django.db.models.JSONField`:

  - There is no way to distinguish between a JSON ``"null"`` (represented by
    ``Value(None, JSONField())``) and a SQL ``null`` (queried using the
    :lookup:`isnull` lookup). Both of these queries return both of these nulls.
  - Some queries with ``Q`` objects, e.g. ``Q(value__foo="bar")``, don't work
    properly, particularly with ``QuerySet.exclude()``.
  - Filtering for a ``None`` key, e.g. ``QuerySet.filter(value__j=None)``
    incorrectly returns objects where the key doesn't exist.
  - You can study the skipped tests in ``DatabaseFeatures.django_test_skips``
    for more details on known issues.

- Pattern matching lookups (:lookup:`iexact`, :lookup:`startswith`,
  :lookup:`istartswith`, :lookup:`endswith`, :lookup:`iendswith`,
  :lookup:`contains`, :lookup:`icontains`, :lookup:`regex`,
  and :lookup:`iregex`) don't support non-string fields.

Database functions
==================

- Some of Django's built-in database functions aren't supported by MongoDB:

  - :class:`~django.db.models.functions.Chr`
  - :class:`~django.db.models.functions.ExtractQuarter`
  - :class:`~django.db.models.functions.LPad`,
    :class:`~django.db.models.functions.RPad`
  - :class:`~django.db.models.functions.MD5`
  - :class:`~django.db.models.functions.Now`
  - :class:`~django.db.models.functions.Ord`
  - :class:`~django.db.models.functions.Repeat`
  - :class:`~django.db.models.functions.Reverse`
  - :class:`~django.db.models.functions.Right`
  - :class:`~django.db.models.functions.SHA1`,
    :class:`~django.db.models.functions.SHA224`,
    :class:`~django.db.models.functions.SHA256`,
    :class:`~django.db.models.functions.SHA384`,
    :class:`~django.db.models.functions.SHA512`
  - :class:`~django.db.models.functions.Sign`

- The ``tzinfo`` parameter of the
  :class:`~django.db.models.functions.TruncDate` and
  :class:`~django.db.models.functions.TruncTime` database functions isn't
  supported.

Transaction management
======================

By default, query execution uses Django and MongoDB's default behavior of autocommit
mode. Each query is immediately committed to the database.

Django's :doc:`transaction management APIs <django:topics/db/transactions>`
are not supported. Instead, this package provides its own :doc:`transaction APIs
</topics/transactions>`.

Database introspection
======================

Due to the lack of ability to introspect MongoDB collection schema,
:djadmin:`inspectdb` and :option:`migrate --fake-initial` aren't supported.

Caching
=======

:ref:`Database caching <database-caching>` is not supported since Django's built-in
database cache backend requires SQL. A custom cache backend for MongoDB may be provided
in the future.
