========================
Encryption API reference
========================

.. module:: django_mongodb_backend.encryption
   :synopsis: Built-in utilities for using Queryable Encryption in MongoDB.

This document covers Queryable Encryption helper functions in
``django_mongodb_backend.encryption``.
Most of the modules contents are designed for development and testing of
Queryable Encryption and are not intended for production use.

``get_auto_encryption_opts()``
==============================

.. function:: get_auto_encryption_opts(key_vault_namespace=None,
   crypt_shared_lib_path=None, kms_providers=None, schema_map=None)

    Returns an :class:`~pymongo.encryption_options.AutoEncryptionOpts` instance
    for use with Queryable Encryption.
