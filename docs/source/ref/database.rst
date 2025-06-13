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

Support for transactions is enabled if the MongoDB configuration supports them:
MongoDB must be configured as a :doc:`replica set <manual:replication>` or
:doc:`sharded cluster <manual:sharding>`, and the store engine must be
:doc:`WiredTiger <manual:core/wiredtiger>`.

If transactions aren't supported (and for any queries run outside of an
:func:`~django.db.transaction.atomic` block), query execution uses Django and
MongoDB's default behavior of autocommit mode. Each query is immediately
committed to the database.

If transactions aren't supported, Django's :doc:`transaction management APIs
<django:topics/db/transactions>` function as no-ops.

Limitations
-----------

MongoDB's transactions have some limitations.

- :meth:`QuerySet.union() <django.db.models.query.QuerySet.union>` is not
  supported.
- If a transaction raises an exception, the transaction is no longer usable.
  For example, if the update stage of :meth:`QuerySet.update_or_create()
  <django.db.models.query.QuerySet.update_or_create>` fails with
  :class:`~django.db.IntegrityError` due to a unique constraint violation, the
  create stage won't be able to proceed.
  :class:`pymongo.errors.OperationFailure` is raised, wrapped by
  :class:`django.db.DatabaseError`.
- Savepoints are not supported.
