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

Helper Functions and Settings
=============================

``KEY_VAULT_COLLECTION_NAME``
-----------------------------

``KEY_VAULT_DATABASE_NAME``
---------------------------

``KEY_VAULT_NAMESPACE``
-----------------------

``KMS_CREDENTIALS``
-------------------

``KMS_PROVIDERS``
-----------------

``QueryType``
-------------

Django settings
===============

``DATABASES["encrypted"]["KMS_CREDENTIALS"]``
---------------------------------------------
