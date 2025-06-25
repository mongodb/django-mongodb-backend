================================
Configuring Queryable Encryption
================================

.. _server-side-queryable-encryption:

Configuring Queryable Encryption in Django is similar to
:doc:`manual:core/queryable-encryption/quick-start` but with some additional
steps required for Django.

Server-side Queryable Encryption
--------------------------------

Server-side Queryable Encryption allows you to begin developing applications
without needing to define the encrypted fields map at the time of connection
to the database.

.. admonition:: What about client-side Queryable Encryption?

    For configuration of client-side Queryable Encryption,
    please refer to this :ref:`see below <client-side-queryable-encryption>`.

Prerequisites
-------------

In addition to :doc:`installing </intro/install>` and
:doc:`configuring </intro/configure>` Django MongoDB Backend,
you will need to install PyMongo with Queryable Encryption support::

    pip install django-mongodb-backend[encryption]

.. admonition:: Queryable Encryption Compatibility

   You can use Queryable Encryption on a MongoDB 7.0 or later replica
   set or sharded cluster, but not a standalone instance.
   :ref:`This table <manual:qe-compatibility-reference>` shows which MongoDB
   server products support which Queryable Encryption mechanisms.

.. _server-side-queryable-encryption-settings:

Settings
--------

Queryable Encryption in Django requires the use of an additional encrypted
database and Key Management Service (KMS) credentials as well as an encrypted
database router. Here's how to set it up in your Django settings.

::

    from django_mongodb_backend import parse_uri
    from pymongo.encryption_options import AutoEncryptionOpts

    DATABASES = {
        "default": parse_uri(
            DATABASE_URL,
            db_name="my_database",
        ),
    }

    DATABASES["encrypted"] = {
        "ENGINE": "django_mongodb_backend",
        "NAME": "my_encrypted_database",
        "OPTIONS": {
            "auto_encryption_opts": AutoEncryptionOpts(
                key_vault_namespace="my_encrypted_database.keyvault",
                kms_providers={"local": {"key": os.urandom(96)}},
            ),
            "directConnection": True,
        },
        "KMS_PROVIDERS": {},
        "KMS_CREDENTIALS": {},
    }

    class EncryptedRouter:
        def allow_migrate(self, db, app_label, model_name=None, **hints):
            # The encryption_ app's models are only created in the encrypted database.
            if app_label == "encryption_":
                return db == "encrypted"
            # Don't create other app's models in the encrypted database.
            if db == "encrypted":
                return False
            return None

        def kms_provider(self, model, **hints):
            return "local"

    DATABASE_ROUTERS = [EncryptedRouter()]

You are now ready to use server-side :doc:`Queryable Encryption
</topics/queryable-encryption>` in your Django project.

.. admonition:: KMS providers and credentials

    The above example uses a local KMS provider with a randomly generated
    key. In a production environment, you should use a secure KMS provider
    such as AWS KMS, Azure Key Vault, or GCP KMS.

    Please refer to :ref:`manual:qe-fundamentals-kms-providers`
    for more information on configuring KMS providers and credentials as well as
    :doc:`manual:core/queryable-encryption/fundamentals/keys-key-vaults`
    for information on creating and managing data encryption keys.

.. _client-side-queryable-encryption:

Client-side Queryable Encryption
--------------------------------

In the :ref:`section above <server-side-queryable-encryption-settings>`,
server-side Queryable Encryption configuration is covered.

Client side Queryable Encryption configuration requires that the entire
encrypted fields map be known at the time of client connection.

Encrypted fields map
~~~~~~~~~~~~~~~~~~~~

In addition to the
:ref:`settings described in the how-to guide <server-side-queryable-encryption-settings>`,
you will need to provide a ``encrypted_fields_map`` to the
``AutoEncryptionOpts``.

Fortunately, this is easy to do with Django MongoDB Backend. You can use
the ``showencryptedfieldsmap`` management command to generate the schema map
for your encrypted fields, and then use the results in your settings.

To generate the encrypted fields map, run the following command in your Django
project::

    python manage.py showencryptedfieldsmap

.. note:: The ``showencryptedfieldsmap`` command is only available if you
   have the ``django_mongodb_backend`` app included in the
   :setting:`INSTALLED_APPS` setting.

Settings
~~~~~~~~

Now include the generated schema map in your Django settings::

    …
    DATABASES["encrypted"] = {
        …
        "OPTIONS": {
            "auto_encryption_opts": AutoEncryptionOpts(
                …
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

You are now ready to use client-side
:doc:`Queryable Encryption </topics/queryable-encryption>`
in your Django project.
