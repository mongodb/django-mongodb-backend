Encrypted models
================

Use :class:`~django_mongodb_backend.models.EncryptedModel` and
:mod:`~django_mongodb_backend.fields` to structure
your data using `Queryable Encryption <https://www.mongodb.com/docs/manual/core/queryable-encryption/>`_.

.. _encrypted-model-field-example:

``EncryptedModelField``
-----------------------

The basics
~~~~~~~~~~

Let's consider this example::

    from django.db import models

    from django_mongodb_backend.models import EncryptedModel
    from django_mongodb_backend.fields import EncryptedCharField
    from django_mongodb_backend.encryption import EqualityQuery


    class Patient(EncryptedModel):
        ssn = EncryptedCharField(max_length=11, queries=EqualityQuery())

        def __str__(self):
            return self.ssn

The API is similar to that of Django's relational fields, with some
security-related changes::

    >>> bob = Patient(ssn="123-45-6789")
    >>> bob.ssn
    '123-45-6789'

Represented in BSON, from an encrypted client connection, the patient data looks like this:

.. code-block:: js

    {
      _id: ObjectId('68825b066fac55353a8b2b41'),
      ssn: '123-45-6789',
      __safeContent__: [b'\xe0)NOFB\x9a,\x08\xd7\xdd\xb8\xa6\xba$…']
    }

The ``ssn`` field is only visible from an encrypted client connection. From an unencrypted client connection,
the patient data looks like this:

.. code-block:: js

    {
      _id: ObjectId('6882566c586a440cd0649e8f'),
      ssn: Binary.createFromBase64('DkrbD67ejkt2u…', 6),
    }

Querying Encrypted Models
~~~~~~~~~~~~~~~~~~~~~~~~~

You can query encrypted fields in encrypted models using a `limited set of
query operators <https://www.mongodb.com/docs/manual/core/queryable-encryption/reference/supported-operations/#std-label-qe-supported-query-operators>`_
which must be specified in the field definition. For example, to query the ``ssn`` field for equality, you can use the
``EqualityQuery`` operator as shown in the example above.

    >>> Patient.objects.get(ssn="123-45-6789").ssn
    '123-45-6789'

If the ``ssn`` field provided in the query matches the encrypted value in the database, the query will succeed.
