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

Helper classes and settings
===========================

For development and testing, users may use the helper functions in
:mod:`~django_mongodb_backend.encryption` to generate the necessary
settings for Queryable Encryption.

Queryable Encryption helper classes and settings are provided to make it easier
configure Queryable Encryption in Django. They are optional, and Queryable
Encryption can be used in Django without them.

``KMS_CREDENTIALS``
-------------------

``KMS_PROVIDERS``
-----------------

``EncryptedRouter``
-------------------

``QueryType``
-------------
