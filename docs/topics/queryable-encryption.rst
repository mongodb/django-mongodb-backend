====================
Queryable Encryption
====================

.. versionadded:: 5.2.3

Once you have successfully set up MongoDB Queryable Encryption as described in
:doc:`the installation guide </howto/queryable-encryption>`, you can start
using encrypted fields in your Django models.

Encrypted fields
================

The basics
----------

:doc:`Encrypted fields </ref/models/encrypted-fields>` may be used to protect
sensitive data like social security numbers, credit card information, or
personal health information. With Queryable Encryption, you can also perform
queries on certain encrypted fields. To use encrypted fields in your models,
import the necessary field types from ``django_mongodb_backend.models`` and
define your models as usual.

Here's the `Python Queryable Encryption Tutorial`_ example implemented in
Django:

.. code-block:: python

    # myapp/models.py
    from django.db import models
    from django_mongodb_backend.models import EmbeddedModel
    from django_mongodb_backend.fields import (
        EmbeddedModelField,
        EncryptedCharField,
        EncryptedEmbeddedModelField,
    )


    class Patient(models.Model):
        patient_name = models.CharField(max_length=255)
        patient_id = models.BigIntegerField()
        patient_record = EmbeddedModelField("PatientRecord")

        def __str__(self):
            return f"{self.patient_name} ({self.patient_id})"


    class PatientRecord(EmbeddedModel):
        ssn = EncryptedCharField(max_length=11)
        billing = EncryptedEmbeddedModelField("Billing")
        bill_amount = models.DecimalField(max_digits=10, decimal_places=2)


    class Billing(EmbeddedModel):
        cc_type = models.CharField(max_length=50)
        cc_number = models.CharField(max_length=20)


Once you have defined your models, create the migrations with ``python manage.py
makemigrations`` and run the migrations with ``python manage.py migrate``. Then
create and manipulate instances of the data just like any other Django model
data. The fields will automatically handle encryption and decryption, ensuring
that sensitive data is stored securely in the database.

.. TODO

.. code-block:: console

    $ python manage.py shell
    >>> from myapp.models import Patient, PatientRecord, Billing
    >>> billing = Billing(cc_type="Visa", cc_number="4111111111111111")
    >>> patient_record = PatientRecord(ssn="123-45-6789", billing=billing)
    >>> patient = Patient.objects.create(
            patient_name="John Doe",
            patient_id=123456789,
            patient_record=patient_record,
        )

.. code-block:: console

    >>> john = Patient.objects.get(name="John Doe")
    >>> john.patient_record.ssn
    '123-45-6789'

.. code-block:: console

    >>> john.patient_record.ssn
    Binary(b'\x0e\x97sv\xecY\x19Jp\x81\xf1\\\x9cz\t1\r\x02...', 6)

Querying encrypted fields
-------------------------

In order to query encrypted fields, you must define the queryable encryption
query type in the model field definition. For example, if you want to query the
``ssn`` field for equality, you can define it as follows:

.. code-block:: python

    class PatientRecord(EmbeddedModel):
        ssn = EncryptedCharField(max_length=11, queries={"queryType": "equality"})
        billing = EncryptedEmbeddedModelField("Billing")
        bill_amount = models.DecimalField(max_digits=10, decimal_places=2)

.. _qe-available-query-types:

Available query types
~~~~~~~~~~~~~~~~~~~~~

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

    >>> patient = Patient.objects.get(patient_record__ssn="123-45-6789")
    >>> patient.name
    'John Doe'

.. admonition:: Range queries vs. lookups

    Range queries in Queryable Encryption are different from Django's
    :ref:`range lookups <django:field-lookups>`
    Range queries allow you to perform comparisons on encrypted fields,
    while Django's range lookups are used for filtering based on a range of
    values.

    For example, if you have an encrypted field that supports range queries, you
    can perform a query like this::

        from myapp.models import Patient

        >>> patients = Patient.objects.filter(patient_record__ssn__gte="123-45-0000",
        ...                                    patient_record__ssn__lte="123-45-9999")

    This will return all patients whose SSN falls within the specified range.

.. _Python Queryable Encryption Tutorial: https://github.com/mongodb/docs/tree/main/content/manual/manual/source/includes/qe-tutorials/python
