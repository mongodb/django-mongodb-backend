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
