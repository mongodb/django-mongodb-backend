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

``showencryptedfieldsmap``
--------------------------

.. versionadded:: 5.2.2

.. django-admin:: showencryptedfieldsmap

    This command shows the mapping of encrypted fields to attributes including
    data type, data keys and query types. It can be used to set the
    ``encrypted_fields_map`` in ``AutoEncryptionOpts``. Defaults to showing
    existing keys from the configured key vault.

    .. django-admin-option:: --database DATABASE

        Specifies the database to use. Defaults to ``default``.

    .. django-admin-option:: --create-data-keys

        If specified, this option will create and show new encryption keys
        instead of showing existing keys from the configured key vault.
