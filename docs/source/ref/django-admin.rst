===================
Management commands
===================

Django MongoDB Backend includes some :doc:`Django management commands
<django:ref/django-admin>`.

Required configuration
======================

To make these commands available, you must include ``"django_mongodb_backend"``
in the :setting:`INSTALLED_APPS` setting.

Available commands
==================

``createcachecollection``
-------------------------

.. django-admin:: createcachecollection

    Creates the cache collection for use with the :doc:`database cache backend
    </topics/cache>` using the information from your :setting:`CACHES` setting.

    .. django-admin-option:: --database DATABASE

        Specifies the database in which the cache collection(s) will be created.
        Defaults to ``default``.


``get_encrypted_fields_map``
----------------------------

.. django-admin:: get_encrypted_fields_map

    Creates a schema map for the encrypted fields in your encrypted models. This
    map can be provided to
    :class:`~pymongo.encryption_options.AutoEncryptionOpts` for use with
    production deployments of :class:`~pymongo.encryption.ClientEncryption`.

    .. django-admin-option:: --database DATABASE

        Specifies the database to use to generate an encrypted fields map
        for all encrypted models. Defaults to ``default``.
