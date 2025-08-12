================================
Configuring Queryable Encryption
================================

.. versionadded:: 5.2.0b2

.. admonition:: Queryable Encryption Compatibility

   You can use Queryable Encryption on a MongoDB 7.0 or later replica
   set or sharded cluster, but not a standalone instance.
   :ref:`This table <manual:qe-compatibility-reference>` shows which MongoDB
   server products support which Queryable Encryption mechanisms.

Configuring Queryable Encryption in Django is similar to
:doc:`manual:core/queryable-encryption/quick-start` but with some additional
steps required for Django.

Prerequisites
-------------

In addition to :doc:`installing </intro/install>` and :doc:`configuring
</intro/configure>` Django MongoDB Backend, you will need to install some
additional packages to use Queryable Encryption. This can be done with the
optional dependency ``encryption`` in the ``django-mongodb-backend`` package::

    pip install django-mongodb-backend[encryption]

Settings
--------

Due to a limited set of
:doc:`manual:core/queryable-encryption/reference/supported-operations`, a second
encrypted database and corresponding database router are needed to use Queryable
Encryption in Django, as well as a KMS provider and credentials.

Here's how to set it up in your Django settings::

    import os

    from django_mongodb_backend import parse_uri
    from pymongo.encryption_options import AutoEncryptionOpts

    DATABASES = {
        …
        "encrypted": parse_uri(
            DATABASE_URL,
            options={
                "auto_encryption_opts": AutoEncryptionOpts(
                    key_vault_namespace="my_encrypted_database.keyvault",
                    kms_providers={"local": {"key": os.urandom(96)}},
                )
            },
            db_name="encrypted",
        ),
    }

    class EncryptedRouter:
        """
        A database router for an encrypted database to be used with a
        "patientdata" app that contains models with encrypted fields.
        """

        def allow_migrate(self, db, app_label, model_name=None, **hints):
            # The patientdata app's models are only created in the encrypted database.
            if app_label == "patientdata":
                return db == "encrypted"
            # Don't create other app's models in the encrypted database.
            if db == "encrypted":
                return False
            return None

        def kms_provider(self, model, **hints):
            return "local"

    DATABASE_ROUTERS = [EncryptedRouter()]

.. admonition:: KMS providers and credentials

    The above example uses a local KMS provider with a randomly generated
    key. In a production environment, you should use a secure KMS provider
    such as AWS KMS, Azure Key Vault, or GCP KMS.

    Please refer to :ref:`manual:qe-fundamentals-kms-providers`
    for more information on configuring KMS providers and credentials as well as
    :doc:`manual:core/queryable-encryption/fundamentals/keys-key-vaults`
    for information on creating and managing data encryption keys.

    You can also refer to the `Python Queryable Encryption Tutorial
    <https://github.com/mongodb/docs/tree/adad2b1ae41ec81a6e5682842850030813adc1e5/source/includes/qe-tutorials/python>`_.

Encrypted fields map
~~~~~~~~~~~~~~~~~~~~

In addition to the :ref:`settings described in the how-to guide
<queryable-encryption-settings>` you will need to provide a
``encrypted_fields_map`` to the ``AutoEncryptionOpts``.

You can use the :djadmin:`showencryptedfieldsmap` management command to generate
the schema map for your encrypted fields and then use the results in your
settings::

    python manage.py showencryptedfieldsmap --database=encrypted

.. admonition:: Didn't work?

    If you get the error ``Unknown command: 'showencryptedfieldsmap'``, ensure
    ``"django_mongodb_backend"`` is in your :setting:`INSTALLED_APPS` setting.

Crypt shared library
~~~~~~~~~~~~~~~~~~~~

Additionally, you will need to ensure that the :ref:`crypt shared library is
available <manual:qe-reference-shared-library>` to your Python environment.
The crypt shared library is recommended over mongocryptd for Queryable
Encryption because it doesn't require an additional daemon process to run to
facilitate Queryable Encryption operations.

Settings
~~~~~~~~

Now include the crypt shared library path and generated schema map in your
Django settings::

    from bson.binary import Binary
    from pymongo.encryption_options import AutoEncryptionOpts

    …
    DATABASES["encrypted"] = {
        …
        "OPTIONS": {
            "auto_encryption_opts": AutoEncryptionOpts(
                …
                crypt_shared_lib_path="/path/to/mongo_crypt_v1",
                encrypted_fields_map = {
                    "encryption__patientrecord": {
                        "fields": [
                            {
                                "bsonType": "string",
                                "path": "ssn",
                                "queries": {"queryType": "equality"},
                                "keyId": Binary(b"\x14F\x89\xde\x8d\x04K7\xa9\x9a\xaf_\xca\x8a\xfb&", 4),
                            },
                        }
                    },
                    # Add other models with encrypted fields here
                },
            ),
            …
        },
        …
    }

You are now ready to use :doc:`Queryable Encryption
</topics/queryable-encryption>`.
