================================
Configuring Queryable Encryption
================================

To use Queryable Encryption with Django MongoDB Backend ensure the following
requirements are met:

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

Django settings
===============

``AUTO_ENCRYPTION_OPTS``
------------------------

``ENCRYPTED_DB_ALIAS``
----------------------

``KEY_VAULT_NAMESPACE``
-----------------------

``KMS_PROVIDERS``
-----------------

``KMS_PROVIDER``
----------------

E.g.::

    from django_mongodb_backend import encryption, parse_uri

    ENCRYPTED_DB_ALIAS = encryption.ENCRYPTED_DB_ALIAS

    KEY_VAULT_NAMESPACE = encryption.get_key_vault_namespace()
    KMS_PROVIDERS = encryption.get_kms_providers()
    KMS_PROVIDER = encryption.KMS_PROVIDER  # "local"

    AUTO_ENCRYPTION_OPTS = encryption.get_auto_encryption_opts(
        key_vault_namespace=KEY_VAULT_NAMESPACE,
        kms_providers=KMS_PROVIDERS,
    )

    DATABASE_URL = os.environ.get("MONGODB_URI", "mongodb://localhost:27017")
    DATABASES = {
        "default": parse_uri(
            DATABASE_URL,
            db_name="test",
        ),
        ENCRYPTED_DB_ALIAS: parse_uri(
            DATABASE_URL,
            options={"auto_encryption_opts": AUTO_ENCRYPTION_OPTS},
            db_name=ENCRYPTED_DB_ALIAS,
        ),
    }
