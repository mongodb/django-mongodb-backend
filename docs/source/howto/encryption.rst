================================
Configuring Queryable Encryption
================================

Configuring Queryable Encryption in Django is similar to
`configuring Queryable Encryption in Python <https://www.mongodb.com/docs/manual/core/queryable-encryption/quick-start/>`_
but with some additional steps to integrate with Django's operations. Below
are the steps needed to set up Queryable Encryption in a Django project.

.. note:: You can use Queryable Encryption on a MongoDB 7.0 or later replica
    set or sharded cluster, but not a standalone instance.
    `This table <https://www.mongodb.com/docs/manual/core/queryable-encryption/reference/compatibility/#std-label-qe-compatibility-reference>`_
    shows which MongoDB server products support which Queryable Encryption mechanisms.

Prerequisites
-------------

In addition to :doc:`installing </intro/install>` and
:doc:`configuring </intro/configure>` Django MongoDB Backend,
you will need to install PyMongo with Queryable Encryption support::

    pip install pymongo[aws,encryption]

Helper classes and settings
===========================

``KMS_CREDENTIALS``
-------------------

``KMS_PROVIDERS``
-----------------

``EncryptedRouter``
-------------------

``QueryType``
-------------
