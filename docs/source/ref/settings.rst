========
Settings
========

.. _queryable-encryption-settings:

Queryable Encryption
====================

The following :setting:`django:DATABASES` inner options support KMS
configuration for Queryable Encryption.

.. setting:: DATABASE-KMS-CREDENTIALS

``KMS_CREDENTIALS``
-------------------

Default: ``{}``

Queryable Encryption requires a KMS provider to encrypt and decrypt data. Django
MongoDB Backend supports configuring KMS credentials and providers for Queryable
Encryption via the ``KMS_CREDENTIALS`` setting in the ``DATABASES``
configuration and the ``kms_provider`` method on the ``DatabaseRouter``.

E.g. to configure AWS KMS credentials:

.. code-block:: python

    KMS_CREDENTIALS = {
        "aws": {
            "key": os.getenv("AWS_KEY_ARN", ""),
            "region": os.getenv("AWS_KEY_REGION", ""),
        },
    }
    DATABASES = {
        # …
    }
    DATABASES["encrypted"]["KMS_CREDENTIALS"] = KMS_CREDENTIALS

Please refer to :ref:`manual:qe-fundamentals-kms-providers` for more information
on configuring KMS providers and credentials as well as
:doc:`manual:core/queryable-encryption/fundamentals/keys-key-vaults` for
information on creating and managing data encryption keys.
