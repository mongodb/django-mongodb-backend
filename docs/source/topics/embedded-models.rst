Embedded models
===============

Use :class:`~django_mongodb_backend.fields.EmbeddedModelField` and
:class:`~django_mongodb_backend.fields.EmbeddedModelArrayField` to structure
your data using `embedded documents
<https://www.mongodb.com/docs/manual/data-modeling/#embedded-data>`_.

.. _embedded-model-field-example:

``EmbeddedModelField``
----------------------

The basics
~~~~~~~~~~

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
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can query into an embedded model using the same double underscore syntax
as relational fields. For example, to retrieve all customers who have an
address with the city "New York"::

    >>> Customer.objects.filter(address__city="New York")

.. _embedded-model-array-field-example:

``EmbeddedModelArrayField``
---------------------------

The basics
~~~~~~~~~~

Let's consider this example::

    from django.db import models

    from django_mongodb_backend.fields import EmbeddedModelArrayField
    from django_mongodb_backend.models import EmbeddedModel


    class Post(models.Model):
        name = models.CharField(max_length=200)
        tags = EmbeddedModelArrayField("Tag")

        def __str__(self):
            return self.name


    class Tag(EmbeddedModel):
        name = models.CharField(max_length=100)

        def __str__(self):
            return self.name


The API is similar to that of Django's relational fields::

    >>> post = Post.objects.create(
    ...     name="Hello world!",
    ...     tags=[Tag(name="welcome"), Tag(name="test")],
    ... )
    >>> post.tags
    [<Tag: welcome>, <Tag: test>]
    >>> post.tags[0].name
    'welcome'

Represented in BSON, the post's structure looks like this:

.. code-block:: js

    {
      _id: ObjectId('683dee4c6b79670044c38e3f'),
      name: 'Hello world!',
      tags: [ { name: 'welcome' }, { name: 'test' } ]
    }
