================================
Configuring Queryable Encryption
================================

To use Queryable Encryption with Django MongoDB Backend first ensure the
following requirements are met:

- Automatic Encryption Shared Library or libmongocrypt must be installed and
  configured.

- The MongoDB server must be Atlas or Enterprise version 7.0 or later.

- Django settings must be updated to include
  :class:`~pymongo.encryption_options.AutoEncryptionOpts`
  with the appropriate configuration for your encryption keys and queryable
  encryption settings.

For development and testing, users may use the helper functions in
:mod:`~django_mongodb_backend.encryption` to generate the necessary
settings for Queryable Encryption.

Helper functions and settings
=============================

KMS providers
-------------

KMS_PROVIDERS
~~~~~~~~~~~~~

E.g.::

    import os

    from django_mongodb_backend import encryption, parse_uri
    from pymongo.encryption import AutoEncryptionOpts

    DATABASE_URL = os.environ.get("MONGODB_URI", "mongodb://localhost:27017")
    DATABASES = {
        "default": parse_uri(
            DATABASE_URL,
            db_name="default",
        ),
        "encrypted": parse_uri(
            DATABASE_URL,
            options={
                "auto_encryption_opts": AutoEncryptionOpts(
                    key_vault_namespace=encryption.KEY_VAULT_NAMESPACE,
                    kms_providers=encryption.KMS_PROVIDERS,
                )
            },
            db_name="encrypted",
        ),
    }
    DATABASES["encrypted"]["KMS_PROVIDERS"] = encryption.KMS_PROVIDERS

KMS_CREDENTIALS
~~~~~~~~~~~~~~~

Python Classes
--------------

``EncryptedRouter``
~~~~~~~~~~~~~~~~~~~

``QueryType``
~~~~~~~~~~~~~
