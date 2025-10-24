================================
Configuring Queryable Encryption
================================

.. versionadded:: 5.2.3

:doc:`manual:core/queryable-encryption` is a powerful MongoDB feature that
allows you to encrypt sensitive fields in your database while still supporting
queries on that encrypted data.

This section will guide you through the process of configuring Queryable
Encryption in your Django project.

.. admonition:: MongoDB requirements

    Queryable Encryption can be used with MongoDB replica sets or sharded
    clusters running version 8.0 or later. Standalone instances are not
    supported. The following table summarizes which MongoDB server products
    support each Queryable Encryption mechanism.

    - :ref:`manual:qe-compatibility-reference`

Installation
============

In addition to the :doc:`installation </intro/install>` and :doc:`configuration
</intro/configure>` steps required to use Django MongoDB Backend, Queryable
Encryption has additional dependencies. You can install these dependencies
by using the ``encryption`` extra when installing ``django-mongodb-backend``:

.. code-block:: console

    $ pip install django-mongodb-backend[encryption]

.. _qe-configuring-databases-setting:

Configuring the ``DATABASES`` setting
=====================================

In addition to the :ref:`database settings <configuring-databases-setting>`
required to use Django MongoDB Backend, Queryable Encryption requires you to
configure a separate encrypted database connection in your
:setting:`django:DATABASES` setting.

.. admonition:: Encrypted database

    An encrypted database is a separate database connection in your
    :setting:`django:DATABASES` setting that is configured to use PyMongo's
    :class:`automatic encryption
    <pymongo.encryption_options.AutoEncryptionOpts>`.

The following example shows how to
configure an encrypted database using the :class:`AutoEncryptionOpts
<pymongo.encryption_options.AutoEncryptionOpts>` from the
:mod:`encryption_options <pymongo.encryption_options>` module with a local KMS
provider and encryption keys stored in the ``encryption.__keyVault`` collection.

.. code-block:: python

    import os

    from pymongo.encryption_options import AutoEncryptionOpts

    DATABASES = {
        "default": {
            "ENGINE": "django_mongodb_backend",
            "HOST": "mongodb+srv://cluster0.example.mongodb.net",
            "NAME": "my_database",
            # ...
        },
        "encrypted": {
            "ENGINE": "django_mongodb_backend",
            "HOST": "mongodb+srv://cluster0.example.mongodb.net",
            "NAME": "my_database_encrypted",
            "USER": "my_user",
            "PASSWORD": "my_password",
            "PORT": 27017,
            "OPTIONS": {
                "auto_encryption_opts": AutoEncryptionOpts(
                    key_vault_namespace="encryption.__keyVault",
                    kms_providers={"local": {"key": os.urandom(96)}},
                )
            },
        },
    }

.. admonition:: Local KMS provider key

    In the example above, a random key is generated for the local KMS provider
    using ``os.urandom(96)``. In a production environment, you should securely
    :ref:`store and manage your encryption keys
    <manual:qe-fundamentals-kms-providers>`.

.. _qe-configuring-database-routers-setting:

Configuring the ``DATABASE_ROUTERS`` setting
============================================

Similar to configuring the :ref:`DATABASE_ROUTERS
<configuring-database-routers-setting>` setting for
:doc:`embedded models </topics/embedded-models>`, Queryable Encryption
requires a :setting:`DATABASE_ROUTERS <django:DATABASE_ROUTERS>` setting to
route database operations to the encrypted database.

The following example shows how to configure a router for the "myapp"
application that routes database operations to the encrypted database for all
models in that application. The router also specifies the :ref:`KMS provider
<qe-configuring-kms>` to use.

.. code-block:: python

    # myapp/routers.py
    class EncryptedRouter:
        def allow_migrate(self, db, app_label, model_name=None, **hints):
            if app_label == "myapp":
                return db == "encrypted"
            # Prevent migrations on the encrypted database for other apps
            if db == "encrypted":
                return False
            return None

        def db_for_read(self, model, **hints):
            if model._meta.app_label == "myapp":
                return "encrypted"
            return None

        db_for_write = db_for_read

Then in your Django settings, add the custom database router to the
:setting:`django:DATABASE_ROUTERS` setting:

.. code-block:: python

    # settings.py
    DATABASE_ROUTERS = ["myapp.routers.EncryptedRouter"]

.. _qe-configuring-kms:

Configuring the Key Management Service (KMS)
============================================

To use Queryable Encryption, you must configure a Key Management Service (KMS)
to store and manage your encryption keys. Django MongoDB Backend allows you to
configure multiple KMS providers and select the appropriate provider for each
model using a custom database router.

The KMS is responsible for managing the encryption keys used to encrypt and
decrypt data. The following table summarizes the available KMS configuration
options followed by an example of how to use them.

+-------------------------------------------------------------------------+--------------------------------------------------------+
| :setting:`KMS_CREDENTIALS <DATABASE-KMS-CREDENTIALS>`                   | A dictionary of Key Management Service (KMS)           |
|                                                                         | credentials configured in the                          |
|                                                                         | :setting:`django:DATABASES` setting.                   |
+-------------------------------------------------------------------------+--------------------------------------------------------+
| :class:`kms_providers <pymongo.encryption_options.AutoEncryptionOpts>`  | A dictionary of KMS provider credentials used to       |
|                                                                         | access the KMS with ``kms_provider``.                  |
+-------------------------------------------------------------------------+--------------------------------------------------------+
| :ref:`kms_provider <qe-configuring-database-routers-setting>`           | A single KMS provider name                             |
|                                                                         | configured in your custom database                     |
|                                                                         | router.                                                |
+-------------------------------------------------------------------------+--------------------------------------------------------+

Example of KMS configuration with ``aws`` in your :class:`kms_providers
<pymongo.encryption_options.AutoEncryptionOpts>` setting:

.. code-block:: python

    from pymongo.encryption_options import AutoEncryptionOpts

    DATABASES = {
        "encrypted": {
            # ...
            "OPTIONS": {
                "auto_encryption_opts": AutoEncryptionOpts(
                    # ...
                    kms_providers={
                        "aws": {
                            "accessKeyId": "your-access-key-id",
                            "secretAccessKey": "your-secret-access-key",
                        },
                    },
                ),
            },
            "KMS_CREDENTIALS": {
                "aws": {
                    "key": os.getenv("AWS_KEY_ARN", ""),
                    "region": os.getenv("AWS_KEY_REGION", ""),
                },
            },
        },
    }

(TODO: If there's a use case for multiple providers, motivate with a use case
and add a test.)

If you've configured multiple KMS providers, you must define logic to determine
the provider for each model in your :ref:`database router
<qe-configuring-database-routers-setting>`::

    class EncryptedRouter:
        # ...
        def kms_provider(self, model, **hints):
            return "aws"

.. _qe-configuring-encrypted-fields-map:

Configuring the ``encrypted_fields_map`` option
===============================================

When you configure the :ref:`DATABASES <qe-configuring-databases-setting>`
setting for Queryable Encryption *without* specifying an
``encrypted_fields_map``, Django MongoDB Backend will create encrypted
collections, including encryption keys, when you :ref:`run migrations for models
that have encrypted fields <qe-migrations>`.

Encryption keys for encrypted fields are stored in the key vault specified in
the :ref:`DATABASES <qe-configuring-kms>` setting. To see the keys created by
Django MongoDB Backend, along with the entire schema, you can run the
:djadmin:`showencryptedfieldsmap` command::

    $ python manage.py showencryptedfieldsmap --database encrypted

Use the output of :djadmin:`showencryptedfieldsmap` to set the
``encrypted_fields_map`` in :class:`AutoEncryptionOpts
<pymongo.encryption_options.AutoEncryptionOpts>` in your Django settings.

.. code-block:: python

    from pymongo.encryption_options import AutoEncryptionOpts
    from bson import json_util

    DATABASES = {
        "encrypted": {
            # ...
            "OPTIONS": {
                "auto_encryption_opts": AutoEncryptionOpts(
                    # ...
                    encrypted_fields_map=json_util.loads(
                        """{
                        "encrypt_patient": {
                          "fields": [
                            {
                              "bsonType": "string",
                              "path": "patient_record.ssn",
                              "keyId": {
                                "$binary": {
                                  "base64": "2MA29LaARIOqymYHGmi2mQ==",
                                  "subType": "04"
                                }
                              },
                              "queries": {
                                "queryType": "equality"
                              }
                            },
                          ]
                        }
                    }"""
                    ),
                )
            },
        },
    }


.. admonition:: Security consideration

   Supplying an encrypted fields map provides more security than relying on an
   encrypted fields map obtained from the server. It protects against a
   malicious server advertising a false encrypted fields map.

Configuring the Automatic Encryption Shared Library
===================================================

The :ref:`manual:qe-reference-shared-library` is a preferred alternative to
:ref:`manual:qe-mongocryptd` and does not require you to start another process
to perform automatic encryption.

In practice, if you use Atlas or Enterprise MongoDB, ``mongocryptd`` is already
configured for you, however in such cases the shared library is still
recommended for use with Queryable Encryption.

You can :ref:`download the shared library
<manual:qe-csfle-shared-library-download>` from the
:ref:`manual:enterprise-official-packages` and configure it in your Django
settings using the ``crypt_shared_lib_path`` option in
:class:`AutoEncryptionOpts <pymongo.encryption_options.AutoEncryptionOpts>`.

The following example shows how to configure the shared library in your Django
settings:

.. code-block:: python

    from pymongo.encryption_options import AutoEncryptionOpts

    DATABASES = {
        "encrypted": {
            # ...
            "OPTIONS": {
                "auto_encryption_opts": AutoEncryptionOpts(
                    # ...
                    crypt_shared_lib_path="/path/to/mongo_crypt_shared_v1.dylib",
                )
            },
            # ...
        },
    }

Configuring the ``EncryptedModelAdmin``
=======================================

When using the :doc:`the Django admin site <django:ref/contrib/admin/index>`
with models that have encrypted fields, use the :class:`EncryptedModelAdmin`
class to ensure that encrypted fields are handled correctly. To do this, inherit
from :class:`EncryptedModelAdmin` in your admin classes instead of the standard
:class:`~django.contrib.admin.ModelAdmin`.

.. code-block:: python

    # myapp/admin.py
    from django.contrib import admin
    from .models import Patient
    from django_mongodb_backend.admin import EncryptedModelAdmin


    @admin.register(Patient)
    class PatientAdmin(EncryptedModelAdmin):
        pass

You are now ready to :doc:`start developing applications
</topics/queryable-encryption>` with Queryable Encryption!
