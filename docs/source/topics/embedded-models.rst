Embedded models
===============

Use :class:`~django_mongodb_backend.fields.EmbeddedModelField` to structure
your data using `embedded documents
<https://www.mongodb.com/docs/manual/data-modeling/#embedded-data>`_.

The basics
----------

Let's consider this example::

   from django_mongodb_backend.fields import EmbeddedModelField
   from django_mongodb_backend.models import EmbeddedModel

   class Customer(models.Model):
       name = models.CharField(...)
       address = EmbeddedModelField("Address")
       ...

   class Address(EmbeddedModel):
       ...
       city = models.CharField(...)


The API is similar to that of Django's relational fields::

   >>> Customer.objects.create(name="Bob", address=Address(city="New York", ...), ...)
   >>> bob = Customer.objects.get(...)
   >>> bob.address
   <Address: Address object>
   >>> bob.address.city
   'New York'

Represented in BSON, Bob's structure looks like this:

.. code-block:: js

   {
     "_id": ObjectId(...),
     "name": "Bob",
     "address": {
       ...
       "city": "New York"
     },
     ...
   }

Querying ``EmbeddedModelField``
-------------------------------

You can query into an embedded model using the same double underscore syntax
as relational fields. For example, to retrieve all customers who have an
address with the city "New York"::

    >>> Customer.objects.filter(address__city="New York")
