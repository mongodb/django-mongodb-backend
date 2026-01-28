========
Settings
========

The document describes Django settings for MongoDB Backend beyond
:doc:`Django's built-in settings <django:ref/settings>`.

Queryable Encryption
====================

An inner option of :setting:`django:DATABASES` configures Key Management
Service (KMS) credentials for Queryable Encryption:

.. setting:: DATABASE-KMS-CREDENTIALS

``KMS_CREDENTIALS``
-------------------

.. versionadded:: 6.0.1

Default: not defined

A dictionary of Key Management Service (KMS) credential key-value pairs. These
credentials are required to access your KMS provider (such as AWS KMS, Azure
Key Vault, or GCP KMS) for encrypting and decrypting data using Queryable
Encryption.

The keys for each provider are documented under the ``master_key`` parameter of
:meth:`~pymongo.encryption.ClientEncryption.create_data_key`. For an example,
see :ref:`configuring-kms`.
