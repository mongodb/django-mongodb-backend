.. _queryable-encryption:

====================
Queryable Encryption
====================

*Added in version 5.2.0b2.*

Django MongoDB Backend supports :doc:`manual:core/queryable-encryption` which
allows you to use :ref:`encrypted fields <encrypted-fields>` to store sensitive
data in MongoDB.

.. _encrypted-field-example:

The basics
==========

Let's consider this example::

    from django.db import models

    from django_mongodb_backend.fields import EncryptedCharField


    class Patient(models.Model):
        ssn = EncryptedCharField(
            max_length=11, queries={"queryType": "equality"}
        )

        def __str__(self):
            return self.ssn

Querying encrypted fields
=========================

The ``ssn`` field is only visible from an encrypted client connection. From an
unencrypted client connection, the patient data looks like this:

.. code-block:: js

    {
      _id: ObjectId('6882566c586a440cd0649e8f'),
      ssn: Binary.createFromBase64('DkrbD67ejkt2u…', 6),
    }

You can query encrypted fields using the :ref:`supported query type options
<manual:qe-fundamentals-encrypt-query>` which must be specified in the
field definition. For example, to query the ``ssn`` field for equality, you
can use the ``{"queryType": "equality"}`` operator as shown in the example
above.

    >>> Patient.objects.get(ssn="123-45-6789").ssn
    '123-45-6789'

If the ``ssn`` field provided in the query matches the encrypted value in the
database, the query will succeed.

Represented in BSON, from an encrypted client connection, the patient data
looks like this:

.. code-block:: js

    {
      _id: ObjectId('68825b066fac55353a8b2b41'),
      ssn: '123-45-6789',
      __safeContent__: [b'\xe0)NOFB\x9a,\x08\xd7\xdd\xb8\xa6\xba$…']
    }

.. admonition:: List of encrypted fields

    See the full list of :ref:`encrypted fields <encrypted-fields>` in the
    :doc:`/ref/models/fields`. Also see
    :doc:`manual:core/queryable-encryption/features` for an explanation of
    encrypted field data.
