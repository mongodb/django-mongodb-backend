================================
Configuring Queryable Encryption
================================

Configuring Queryable Encryption in Django is similar to
`configuring Queryable Encryption in Python <https://www.mongodb.com/docs/manual/core/queryable-encryption/quick-start/>`_
but with some additional steps to integrate with Django's operations. Below
are the steps needed to set up Queryable Encryption in a Django project.

Prerequisites
-------------

.. note:: You can use Queryable Encryption on a MongoDB 7.0 or later replica
    set or sharded cluster, but not a standalone instance.
    `This table <https://www.mongodb.com/docs/manual/core/queryable-encryption/reference/compatibility/#std-label-qe-compatibility-reference>`_
    shows which MongoDB server products support which Queryable Encryption mechanisms.

In addition to :doc:`installing </intro/install>` and
:doc:`configuring </intro/configure>` Django MongoDB Backend,
you will need to install PyMongo with Queryable Encryption support::

    pip install django-mongodb-backend[encryption]

Settings
--------

Add an encrypted database, encrypted database router and KMS credentials to
your Django settings.

.. note:: Use of the helpers provided in ``django_mongodb_backend.encryption``
    requires an encrypted database named "other".

::

    from django_mongodb_backend import encryption
    from pymongo.encryption import AutoEncryptionOpts

    DATABASES = {
        "default": parse_uri(
            MONGODB_URI,
            db_name="my_database",
        ),
        "other": parse_uri(
            MONGODB_URI,
            db_name="other",
            options={
                "auto_encryption_opts": AutoEncryptionOpts(
                    kms_providers=encryption.KMS_PROVIDERS,
                    key_vault_namespace="other.keyvault",
                )
            },
        ),

    DATABASES["other"]["KMS_CREDENTIALS"] = encryption.KMS_CREDENTIALS
    DATABASE_ROUTERS = [encryption.EncryptedRouter()]

You are now ready to use :doc:`Queryable Encryption </topics/queryable-encryption>` in your Django project.


Helper classes and settings
===========================

``KMS_CREDENTIALS``
-------------------

``KMS_PROVIDERS``
-----------------

``EncryptedRouter``
-------------------

Query Types
-----------

- ``EqualityQuery``
- ``RangeQuery``
