===================
Utils API reference
===================

.. module:: django_mongodb_backend.utils
   :synopsis: Built-in utilities.

This document covers the public API parts of ``django_mongodb_backend.utils``.
Most of the module's contents are designed for internal use and only the
following parts can be considered stable.

``parse_uri()``
===============

.. function:: parse_uri(uri, db_name=None, options=None, test=None)

    .. deprecated:: 5.2.2

        ``parse_uri()`` is deprecated in favor of putting the connection string
        in ``DATABASES["HOST"]``. See :ref:`the deprecation timeline
        <parse-uri-deprecation>` for upgrade instructions.

    Parses a MongoDB `connection string`_ into a dictionary suitable for
    Django's :setting:`DATABASES` setting.

    .. _connection string: https://www.mongodb.com/docs/manual/reference/connection-string/

    Example::

        import django_mongodb_backend

        MONGODB_URI = "mongodb+srv://my_user:my_password@cluster0.example.mongodb.net/defaultauthdb?retryWrites=true&w=majority&tls=false"
        DATABASES["default"] = django_mongodb_backend.parse_uri(MONGODB_URI, db_name="example")

    You must specify ``db_name`` (the :setting:`NAME` of your database) if the
    URI doesn't specify ``defaultauthdb``.

    You can use the parameters to customize the resulting :setting:`DATABASES`
    setting:

    - Use ``options`` to provide a dictionary of parameters to
      :class:`~pymongo.mongo_client.MongoClient`. These will be merged with
      (and, in the case of duplicates, take precedence over) any options
      specified in the URI.

    - Use ``test`` to provide a dictionary of settings for test databases in
      the format of :setting:`TEST <DATABASE-TEST>`.

    But for maximum flexibility, construct :setting:`DATABASES` manually as
    described in :ref:`configuring-databases-setting`.

``model_has_encrypted_fields()``
=================================

.. function:: model_has_encrypted_fields(model)

    .. versionadded:: 5.2.3

    Returns ``True`` if the given Django model has any fields that use
    encrypted models.

    Example usage in a :ref:`database router
    <qe-configuring-database-routers-setting>`::

        from django_mongodb_backend.utils import model_has_encrypted_fields

        class EncryptedRouter:
            def db_for_read(self, model, **hints):
                if model_has_encrypted_fields(model):
                    return "encrypted"
                return "default"

            def db_for_write(self, model, **hints):
                if model_has_encrypted_fields(model):
                    return "encrypted"
                return "default"

            def allow_migrate(self, db, app_label, model_name=None, **hints):
                if hints.get("model"):
                    if model_has_encrypted_fields(hints["model"]):
                        return db == "encrypted"
                    else:
                        return db == "default"
                return None
