Model reference
===============

.. module:: django_mongodb_backend.models

Two MongoDB-specific models are available in ``django_mongodb_backend.models``.

.. class:: EmbeddedModel

    An abstract model which all :doc:`embedded models </topics/embedded-models>`
    must subclass.

    Since these models are not stored in their own collection, they do not have
    any of the normal ``QuerySet`` methods (``all()``, ``filter()``,
    ``delete()``, etc.) You also cannot call ``Model.save()`` and ``delete()``
    on them.

    Embedded model instances won't have a value for their primary key unless
    one is explicitly set.

.. class:: EncryptedModel

    An abstract model which all :doc:`encrypted models </topics/encrypted-models>`
    must subclass.

    Encrypted models support the use of encrypted fields which are
    encrypted automatically with MongoDB's Queryable Encryption feature.
