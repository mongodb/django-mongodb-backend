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

Here are models based on the `Python Queryable Encryption Tutorial`_::

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

.. _Python Queryable Encryption Tutorial: https://github.com/mongodb/docs/tree/main/content/manual/manual/source/includes/qe-tutorials/python

.. _qe-migrations:

Migrations
----------

Once you have defined your models, create migrations with:

.. code-block:: console

    $ python manage.py makemigrations

Then run the migrations with:

.. code-block:: console

    $ python manage.py migrate --database encrypted

Now create and manipulate instances of the data just like any other Django
model data. The fields will automatically handle encryption and decryption,
ensuring that :ref:`sensitive data is stored securely in the database
<manual:qe-features-encryption-at-rest>`.

Routers
-------

The example above requires a :ref:`database router
<qe-configuring-database-routers-setting>` to direct operations on models with
encrypted fields to the appropriate database. It also requires the use of a
:ref:`router for embedded models <configuring-database-routers-setting>`. Here
is an example that includes both::

    # myproject/settings.py
    DATABASE_ROUTERS = [
        "django_mongodb_backend.routers.MongoRouter",
        "myproject.routers.EncryptedRouter",
    ]

Querying encrypted fields
-------------------------

In order to query encrypted fields, you must define the queryable encryption
query type in the model field definition. For example, if you want to query the
``ssn`` field for equality, you can define it as follows::

    class PatientRecord(EmbeddedModel):
        ssn = EncryptedCharField(max_length=11, queries={"queryType": "equality"})
        billing = EncryptedEmbeddedModelField("Billing")
        bill_amount = models.DecimalField(max_digits=10, decimal_places=2)

Then you can perform a query like this:

.. code-block:: console

    >>> patient = Patient.objects.get(patient_record__ssn="123-45-6789")
    >>> patient.name
    'John Doe'

.. _qe-available-query-types:

Available query types
~~~~~~~~~~~~~~~~~~~~~

The ``queries`` option should be a dictionary that specifies the type of queries
that can be performed on the field. Of the :ref:`available query types
<manual:qe-fundamentals-encrypt-query>` Django MongoDB Backend currently
supports:

- ``equality``
- ``range``

.. admonition:: Query types vs. Django lookups

    Range queries in Queryable Encryption are different from Django's
    :ref:`range lookups <django:field-lookups>`. Range queries allow you to
    perform comparisons on encrypted fields, while Django's range lookups are
    used for filtering based on a range of values.

QuerySet limitations
~~~~~~~~~~~~~~~~~~~~

In addition to :ref:`Django MongoDB Backend's QuerySet limitations
<known-issues-limitations-querying>`,

.. TODO
