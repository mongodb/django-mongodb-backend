================
Database caching
================

.. class:: django_mongodb_backend.cache.MongoDBCache

You can configure :doc:`Django's caching API <django:topics/cache>` to store
its data in MongoDB.

To use a database collection as your cache backend:

* Set :setting:`BACKEND <CACHES-BACKEND>` to
  ``django_mongodb_backend.cache.MongoDBCache``

* Set :setting:`LOCATION <CACHES-LOCATION>` to ``collection_name``, the name of
  the MongoDB collection. This name can be whatever you want, as long as it's a
  valid collection name that's not already being used in your database.

In this example, the cache collection's name is ``my_cache_collection``::

    CACHES = {
        "default": {
            "BACKEND": "django_mongodb_backend.cache.MongoDBCache",
            "LOCATION": "my_cache_collection",
        },
    }

Unlike other cache backends, the database cache does not support automatic
culling of expired entries at the database level. Instead, expired cache
entries are culled each time ``add()``, ``set()``, or ``touch()`` is called.

Creating the cache collection
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Before using the database cache, you must create the cache collection with this
command:

.. code-block:: shell

    python manage.py createcachecollection

.. admonition:: Didn't work?

    If you get the error ``Unknown command: 'createcachecollection'``, ensure
    ``"django_mongodb_backend"`` is in your :setting:`INSTALLED_APPS` setting.

This creates a collection in your database with the proper indexes. The name of
the collection is taken from :setting:`LOCATION <CACHES-LOCATION>`.

If you are using multiple database caches, :djadmin:`createcachecollection`
creates one collection for each cache.

If you are using multiple databases, :djadmin:`createcachecollection` observes
the ``allow_migrate()`` method of your database routers (see the
:ref:`database-caching-multiple-databases` section of Django's caching docs).

Like :djadmin:`migrate`, :djadmin:`createcachecollection` won't touch an
existing collection. It will only create missing collections.
