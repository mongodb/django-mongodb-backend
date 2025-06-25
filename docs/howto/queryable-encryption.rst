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
</intro/configure>` steps for Django MongoDB Backend, Queryable
Encryption requires encryption support and a Key Management Service (KMS).

You can install encryption support with the following command::

    pip install django-mongodb-backend[encryption]

.. _qe-configuring-databases-setting:

Configuring the ``DATABASES`` setting
=====================================

In addition to :ref:`configuring-databases-setting`, you must also configure an
encrypted database in your :setting:`django:DATABASES` setting.

This database will be used to store encrypted fields in your models. The
following example shows how to configure an encrypted database using the
:class:`AutoEncryptionOpts <pymongo.encryption_options.AutoEncryptionOpts>` from the
:mod:`encryption_options <pymongo.encryption_options>` module.

This example uses a local KMS provider and a key vault namespace for storing
encryption keys.

.. code-block:: python

    import os

    from pymongo.encryption_options import AutoEncryptionOpts

    DATABASES = {
        "default": {
            "ENGINE": "django_mongodb_backend",
            "HOST": "mongodb+srv://cluster0.example.mongodb.net",
            "NAME": "my_database",
            "USER": "my_user",
            "PASSWORD": "my_password",
            "PORT": 27017,
            "OPTIONS": {
                "retryWrites": "true",
                "w": "majority",
                "tls": "false",
            },
        },
        "encrypted": {
            "ENGINE": "django_mongodb_backend",
            "HOST": "mongodb+srv://cluster0.example.mongodb.net",
            "NAME": "encrypted",
            "USER": "my_user",
            "PASSWORD": "my_password",
            "PORT": 27017,
            "OPTIONS": {
                "auto_encryption_opts": AutoEncryptionOpts(
                    key_vault_namespace="encrypted.keyvault",
                    kms_providers={"local": {"key": os.urandom(96)}},
                )
            },
        },
    }

.. _qe-configuring-database-routers-setting:

Configuring the ``DATABASE_ROUTERS`` setting
============================================

Similar to :ref:`configuring-database-routers-setting` for using :doc:`embedded
models </topics/embedded-models>`, to use Queryable Encryption you must also
configure the :setting:`django:DATABASE_ROUTERS` setting to route queries to the
encrypted database.

This is done by adding a custom router that routes queries to the encrypted
database based on the model's metadata. The following example shows how to
configure a custom router for Queryable Encryption:

.. code-block:: python

    class EncryptedRouter:
        """
        A router for routing queries to the encrypted database for Queryable
        Encryption.
        """

        def db_for_read(self, model, **hints):
            if model._meta.app_label == "myapp":
                return "encrypted"
            return None

        db_for_write = db_for_read

        def allow_migrate(self, db, app_label, model_name=None, **hints):
            if app_label == "myapp":
                return db == "encrypted"
            # Don't create other app's models in the encrypted database.
            if db == "encrypted":
                return False
            return None

        def kms_provider(self, model, **hints):
            return "local"


    DATABASE_ROUTERS = [EncryptedRouter]

.. _qe-configuring-kms:

Configuring the Key Management Service (KMS)
============================================

To use Queryable Encryption, you must configure a Key Management Service (KMS).
The KMS is responsible for managing the encryption keys used to encrypt and
decrypt data. The following table summarizes the available KMS configuration
options followed by an example of how to use them.

+-------------------------------------------------------------------------+--------------------------------------------------------+
| :setting:`KMS_CREDENTIALS <DATABASE-KMS-CREDENTIALS>`                   | A dictionary of Key Management Service (KMS)           |
|                                                                         | credentials configured in the                          |
|                                                                         | :setting:`django:DATABASES` setting.                   |
+-------------------------------------------------------------------------+--------------------------------------------------------+
| :class:`kms_providers <pymongo.encryption_options.AutoEncryptionOpts>`  | A dictionary of KMS provider credentials used to       |
|                                                                         | access the KMS with                                    |
|                                                                         | :setting:`KMS_CREDENTIALS <DATABASE-KMS-CREDENTIALS>`. |
+-------------------------------------------------------------------------+--------------------------------------------------------+
| ``kms_provider``                                                        | A single KMS provider name                             |
|                                                                         | configured in your custom database                     |
|                                                                         | router.                                                |
+-------------------------------------------------------------------------+--------------------------------------------------------+

Example of KMS configuration with AWS KMS:

.. code-block:: python

    from pymongo.encryption_options import AutoEncryptionOpts

    DATABASES = {
        "encrypted": {
            "ENGINE": "django_mongodb_backend",
            "HOST": "mongodb+srv://cluster0.example.mongodb.net",
            "NAME": "encrypted",
            "USER": "my_user",
            "PASSWORD": "my_password",
            "PORT": 27017,
            "OPTIONS": {
                "auto_encryption_opts": AutoEncryptionOpts(
                    key_vault_namespace="encrypted.keyvault",
                    kms_providers={
                        "aws": {
                            "accessKeyId": "your-access-key-id",
                            "secretAccessKey": "your-secret-access-key",
                        }
                    },
                )
            },
            "KMS_CREDENTIALS": {
                "aws": {
                    "key": os.getenv("AWS_KEY_ARN", ""),
                    "region": os.getenv("AWS_KEY_REGION", ""),
                },
            },
        },
    }


    class EncryptedRouter:
        # ...
        def kms_provider(self, model, **hints):
            return "aws"

.. _qe-configuring-encrypted-fields-map:

Configuring the ``encrypted_fields_map``
========================================

When you :ref:`configure an encrypted database connection
<qe-configuring-databases-setting>` without specifying an
``encrypted_fields_map``, Django MongoDB Backend will create encrypted
collections for you when you run ``python manage.py migrate``.

Encryption keys for encrypted fields are stored in the key vault
:ref:`specified in the Django settings <qe-configuring-kms>`. To see the keys
created by Django MongoDB Backend, along with the entire schema, you can run the
:djadmin:`showencryptedfieldsmap` command::

    $ python manage.py showencryptedfieldsmap --database encrypted

Use the output of the :djadmin:`showencryptedfieldsmap` command to set the
``encrypted_fields_map`` in
:class:`pymongo.encryption_options.AutoEncryptionOpts` in your Django settings.

.. code-block:: python

    from pymongo.encryption_options import AutoEncryptionOpts
    from bson import json_util

    DATABASES = {
        "encrypted": {
            "ENGINE": "django_mongodb_backend",
            "HOST": "mongodb+srv://cluster0.example.mongodb.net",
            "NAME": "encrypted",
            "USER": "my_user",
            "PASSWORD": "my_password",
            "PORT": 27017,
            "OPTIONS": {
                "auto_encryption_opts": AutoEncryptionOpts(
                    key_vault_namespace="encrypted.keyvault",
                    kms_providers={
                        "aws": {
                            "accessKeyId": "your-access-key-id",
                            "secretAccessKey": "your-secret-access-key",
                        }
                    },
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
:class:`pymongo.encryption_options.AutoEncryptionOpts`. The following example
shows how to configure the shared library in your Django settings:

.. code-block:: python

    from pymongo.encryption_options import AutoEncryptionOpts

    DATABASES = {
        "encrypted": {
            "ENGINE": "django_mongodb_backend",
            "HOST": "mongodb+srv://cluster0.example.mongodb.net",
            "NAME": "encrypted",
            "USER": "my_user",
            "PASSWORD": "my_password",
            "PORT": 27017,
            "OPTIONS": {
                "auto_encryption_opts": AutoEncryptionOpts(
                    key_vault_namespace="encrypted.keyvault",
                    kms_providers={
                        "aws": {
                            "accessKeyId": "your-access-key-id",
                            "secretAccessKey": "your-secret-access-key",
                        }
                    },
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
                    crypt_shared_lib_path="/path/to/mongo_crypt_shared_v1.dylib",
                )
            },
            "KMS_CREDENTIALS": {
                "aws": {
                    "key": os.getenv("AWS_KEY_ARN", ""),
                    "region": os.getenv("AWS_KEY_REGION", ""),
                },
            },
        },
    }

You are now ready to :doc:`start developing applications
</topics/queryable-encryption>` with Queryable Encryption!
