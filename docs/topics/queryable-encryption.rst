====================
Queryable Encryption
====================

.. versionadded:: 5.2.1

Once you have configured your Django project and MongoDB deployment for
Queryable Encryption, you’re ready to start developing applications that take
advantage of these enhanced security features.

Encrypted fields
================

You can use :doc:`encrypted fields </ref/models/encrypted-fields>` to structure
your sensitive data.


The basics
----------

For example, you can define a model with encrypted fields
like this:

.. code-block:: python

    from django.db import models
    from django_mongodb_backend.fields import EncryptedCharField


    class Patient(models.Model):
        name = models.CharField(max_length=255)
        ssn = EncryptedCharField(max_length=11)

        def __str__(self):
            return self.name

Once you have defined your model, created migrations with ``python manage.py
makemigrations`` and run migrations with ``python manage.py migrate``, you can
create and manipulate instances of the data just like any other Django model
data. The fields will automatically handle encryption and decryption, ensuring
that sensitive data is stored securely in the database.

From an encrypted client, you can access the data::

    from myapp.models import Patient

    >>> bob = Patient.objects.create(name="Bob", ssn="123-45-6789")
    >>> bob.ssn
    '123-45-6789'

From an unencrypted client, you can still access the data, but the sensitive
fields will be encrypted. For example, if you try to access the ``ssn`` field
from an unencrypted client, you will see the encrypted value::

    from myapp.models import Patient

    >>> bob = Patient.objects.get(name="Bob")
    >>> bob.ssn
    Binary(b'\x0e\x97sv\xecY\x19Jp\x81\xf1\\\x9cz\t1\r\x02...', 6)

Querying encrypted fields
-------------------------

In order to query encrypted fields, you must define the queryable encryption
query type in the model field definition. For example, if you want to query the
``ssn`` field for equality, you can define it as follows:

.. code-block:: python

    from django.db import models
    from django_mongodb_backend.fields import EncryptedCharField


    class Patient(models.Model):
        name = models.CharField(max_length=255)
        ssn = EncryptedCharField(max_length=11, queries={"queryType": "equality"})

        def __str__(self):
            return self.name

Query types
~~~~~~~~~~~

The ``queries`` option should be a dictionary that specifies the type of queries
that can be performed on the field. The :ref:`available query types
<manual:qe-fundamentals-encrypt-query>` are as follows:

- ``equality``: Supports equality queries.
- ``range``: Supports range queries.

You can configure an encrypted field for either equality or range queries, but
not both.

Now you can perform queries on the ``ssn`` field using the defined query type.
For example, to find a patient by their SSN, you can do the following::

    from myapp.models import Patient

    >>> patient = Patient.objects.get(ssn="123-45-6789")
    >>> patient.name
    'Bob'


QuerySet Limitations
~~~~~~~~~~~~~~~~~~~~

When using Django QuerySets with MongoDB Queryable Encryption, it’s important to
understand that many typical ORM features are restricted because the database
only sees encrypted ciphertext, not plaintext. This means that only certain
query types are supported, and a lot of filtering, sorting, and aggregating must
be done client-side after decryption. Key limitations include:

- **Equality only filtering** – You can filter encrypted fields using exact
  matches, but operators like contains, startswith, regex, or unsupported range
  lookups will not work.
- **No server-side sorting** – .order_by() on encrypted fields won’t produce
  meaningful results; sorting needs to happen after decryption in Python.
- **No server-side aggregation** – Functions like annotate() or aggregate()
  won’t operate on encrypted fields; you must aggregate locally after fetching
  data.
- **Index constraints** – Queries are only possible on encrypted fields that
  have a configured queryable encryption index and keys available on the client.
- **No joins on encrypted fields** – Filtering across relationships using
  encrypted foreign keys is unsupported because matching must happen
  client-side.
- **Admin/debug limitations** – You’ll need to integrate client-side decryption
  for Django admin or tools, otherwise you’ll see ciphertext.

In short, when working with Queryable Encryption, design your queries to use
exact matches only on encrypted fields, and plan to handle any sorting or
aggregation after results are decrypted in your application code.
