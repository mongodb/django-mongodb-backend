==================
Database reference
==================

This document supplements :doc:`Django's documentation on databases
<django:ref/databases>`.

Persistent connections
======================

Persistent connections avoid the overhead of reestablishing a connection to
the database in each HTTP request. They're normally controlled by the
:setting:`CONN_MAX_AGE` parameter which defines the maximum lifetime of a
connection. However, this parameter is unnecessary and has no effect with
Django MongoDB Backend because Django's API for connection-closing
(``django.db.connection.close()``) has no effect. In other words, persistent
connections are enabled by default.

.. versionadded:: 5.2.0b0

    Support for connection pooling was added.  In older versions, use
    :setting:`CONN_MAX_AGE` to enable persistent connections.

.. _connection-management:

Connection management
=====================

Django uses this backend to open a connection pool to the database when it
first makes a database query. It keeps this pool open and reuses it in
subsequent requests.

The underlying :class:`~pymongo.mongo_client.MongoClient` takes care connection
management, so the :setting:`CONN_HEALTH_CHECKS` setting is unnecessary and has
no effect.

Django's API for connection-closing (``django.db.connection.close()``) has no
effect. Rather, if you need to close the connection pool, use
``django.db.connection.close_pool()``.

.. versionadded:: 5.2.0b0

    Support for connection pooling and ``connection.close_pool()`` were added.

.. _transactions:

Transactions
============

.. versionadded:: 5.2.0b2

Support for :doc:`Django's transactions APIs <django:topics/db/transactions>`
is enabled if MongoDB is configured as a :doc:`replica set<manual:replication>`
or a :doc:`sharded cluster <manual:sharding>`.

If transactions aren't supported, query execution uses Django and MongoDB's
default behavior of autocommit mode. Each query is immediately committed to the
database. Django's transaction management APIs, such as
:func:`~django.db.transaction.atomic`, function as no-ops.

.. _transactions-limitations:

Limitations
-----------

MongoDB's transaction limitations that are applicable to Django are:

- :meth:`QuerySet.union() <django.db.models.query.QuerySet.union>` is not
  supported inside a transaction.
- If a transaction raises an exception, the transaction is no longer usable.
  For example, if the update stage of :meth:`QuerySet.update_or_create()
  <django.db.models.query.QuerySet.update_or_create>` fails with
  :class:`~django.db.IntegrityError` due to a unique constraint violation, the
  create stage won't be able to proceed.
  :class:`pymongo.errors.OperationFailure` is raised, wrapped by
  :class:`django.db.DatabaseError`.
- Savepoints (i.e. nested :func:`~django.db.transaction.atomic` blocks) aren't
  supported. The outermost :func:`~django.db.transaction.atomic` will start
  a transaction while any subsequent :func:`~django.db.transaction.atomic`
  blocks will have no effect.
- Migration operations aren't :ref:`wrapped in a transaction
  <topics/migrations:transactions>` because of MongoDB restrictions such as
  adding indexes to existing collections while in a transaction.
