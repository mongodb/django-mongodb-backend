========
Settings
========

.. _queryable-encryption-settings:

Queryable Encryption
====================

The following :setting:`django:DATABASES` inner options support configuration of
Key Management Service (KMS) credentials for Queryable Encryption.

.. setting:: DATABASE-KMS-CREDENTIALS

``KMS_CREDENTIALS``
-------------------

Default: ``{}`` (empty dictionary)

A dictionary of Key Management Service (KMS) credential key-value pairs. These
credentials are required to access your KMS provider (such as AWS KMS, Azure Key
Vault, or GCP KMS) for encrypting and decrypting data using Queryable
Encryption.

For example after :doc:`/howto/queryable-encryption`, to configure AWS KMS,
Azure Key Vault, or GCP KMS credentials, you can set ``KMS_CREDENTIALS`` in
your :setting:`django:DATABASES` settings as follows:

.. code-block:: python

    DATABASES["encrypted"]["KMS_CREDENTIALS"] = {
        "aws": {
            "key": os.getenv("AWS_KEY_ARN", ""),
            "region": os.getenv("AWS_KEY_REGION", ""),
        },
        "azure": {
            "key": os.getenv("AZURE_KEY_VAULT_URL", ""),
            "client_id": os.getenv("AZURE_CLIENT_ID", ""),
            "client_secret": os.getenv("AZURE_CLIENT_SECRET", ""),
        },
        "gcp": {
            "key": os.getenv("GCP_KEY_NAME", ""),
            "project_id": os.getenv("GCP_PROJECT_ID", ""),
        },
    }
