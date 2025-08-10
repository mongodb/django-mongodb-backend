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

.. django-admin:: showencryptedfieldsmap

   Show mapping of models and their encrypted fields.

    .. django-admin-option:: --database DATABASE

        Specifies the database to use.
        Defaults to ``default``.

    .. django-admin-option:: --create-new-keys

        If specified, creates the data keys instead of getting them from the
        database.
