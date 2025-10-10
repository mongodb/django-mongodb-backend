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

.. versionadded:: 5.2.3

.. django-admin:: showencryptedfieldsmap

    This command shows the mapping of encrypted fields to attributes including
    data type, data keys and query types. It can be used to set the
    ``encrypted_fields_map`` in ``AutoEncryptionOpts``.

    .. django-admin-option:: --database DATABASE

        Specifies the database to use. Defaults to ``default``.
