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

    This command generates output for includision in
    :class:`~pymongo.encryption_options.AutoEncryptionOpts`\'s
    ``encrypted_fields_map`` argument.

    See :ref:`qe-configuring-encrypted-fields-map`.

    .. django-admin-option:: --database DATABASE

        Specifies the database to use. Defaults to ``default``.
