================================
Configuring Queryable Encryption
================================

.. versionadded:: 5.2.0rc1

.. admonition:: MongoDB requirements

    Queryable Encryption can be used with MongoDB replica sets or sharded
    clusters running version 7.0 or later. Standalone instances are not
    supported. The following table summarizes which MongoDB server products
    support each Queryable Encryption mechanism.

    - :ref:`manual:qe-compatibility-reference`

Installation
============

In addition to the :doc:`installation </intro/install>` and :doc:`configuration
</intro/configure>` steps for Django MongoDB Backend, enabling Queryable
Encryption requires support for encryption and a Key Management Service (KMS).
You can install these additional dependencies with the following command::

    pip install django-mongodb-backend[encryption]

Configuring the ``DATABASES`` setting
=====================================

In addition to :ref:`configuring-databases-setting`, you must also configure an
encrypted database in your ``DATABASES`` setting.

This database will be used to store encrypted fields in your models. The
following example shows how to configure an encrypted database using the
``AutoEncryptionOpts`` from the ``pymongo.encryption_options`` module.

This example uses a local KMS provider and a key vault namespace for storing
encryption keys.

.. code-block:: python

    import os

    from django_mongodb_backend import parse_uri
    from pymongo.encryption_options import AutoEncryptionOpts

    DATABASES = {
        # ...
        "encrypted": parse_uri(
            DATABASE_URL,
            options={
                "auto_encryption_opts": AutoEncryptionOpts(
                    key_vault_namespace="keyvault.keyvault",
                    kms_providers={"local": {"key": os.urandom(96)}},
                )
            },
            db_name="encrypted",
        ),
    }

Configuring the ``DATABASE_ROUTERS`` setting
============================================

Similar to :ref:`configuring-database-routers-setting` for using embedded
models, to use Queryable Encryption, you must also configure the
``DATABASE_ROUTERS`` setting to route queries to the encrypted database.

This is done by adding a custom router that routes queries to the encrypted
database based on the model's metadata. The following example shows how to
configure a custom router for Queryable Encryption:

.. code-block:: python

    class EncryptedRouter:
        """
        A router for routing queries to the encrypted database for Queryable
        Encryption.
        """

        def allow_migrate(self, db, app_label, model_name=None, **hints):
            # The patientdata app's models are only created in the encrypted
            # database.
            if app_label == "patientdata":
                return db == "encrypted"
            # Don't create other app's models in the encrypted database.
            if db == "encrypted":
                return False
            return None

        def kms_provider(self, model, **hints):
            return "local"


    DATABASE_ROUTERS = [EncryptedRouter]

Configuring KMS Providers
=========================
