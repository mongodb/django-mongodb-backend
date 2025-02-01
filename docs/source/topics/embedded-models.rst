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

    from django.db import models

    from django_mongodb_backend.fields import EmbeddedModelField
    from django_mongodb_backend.models import EmbeddedModel


    class Customer(models.Model):
        name = models.CharField(max_length=255)
        address = EmbeddedModelField("Address")

        def __str__(self):
            return self.name


    class Address(EmbeddedModel):
        city = models.CharField(max_length=255)

        def __str__(self):
            return self.city


The API is similar to that of Django's relational fields::

    >>> bob = Customer.objects.create(name="Bob", address=Address(city="New York"))
    >>> bob.address
    <Address: New York>
    >>> bob.address.city
    'New York'

Represented in BSON, the customer structure looks like this:

.. code-block:: js

    {
      _id: ObjectId('683df821ec4bbe0692d43388'),
      name: 'Bob',
      address: { city: 'New York' }
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

Querying ``EmbeddedModelArrayField``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can query into an embedded model array using the same double underscore
syntax as relational fields. For example, to find posts that have a tag with
name "test"::

    >>> Post.objects.filter(tags__name="test")

There are a limited set of lookups you can chain after an embedded field:

* :lookup:`exact`, :lookup:`iexact`
* :lookup:`in`
* :lookup:`gt`, :lookup:`gte`, :lookup:`lt`, :lookup:`lte`

For example, to find posts that have tags with name "test", "TEST", "tEsT",
etc::

>>> Post.objects.filter(tags__name__iexact="test")

.. fieldlookup:: embeddedmodelarrayfield.len

``len`` transform
^^^^^^^^^^^^^^^^^

You can use the ``len`` transform to filter on the length of the array. The
lookups available afterward are those available for
:class:`~django.db.models.IntegerField`. For example, to match posts with one
tag::

    >>> Post.objects.filter(tags__len=1)

or at least one tag::

    >>> Post.objects.filter(tags__len__gte=1)

Index and slice transforms
^^^^^^^^^^^^^^^^^^^^^^^^^^

Like :class:`~django_mongodb_backend.fields.ArrayField`, you can use
:lookup:`index <mongo-arrayfield.index>` and :lookup:`slice
<mongo-arrayfield.slice>` transforms to filter on particular items in an array.

For example, to find posts where the first tag is named "test"::

>>> Post.objects.filter(tags__0__name="test")

Or to find posts where the one of the first two tags is named "test"::

>>> Post.objects.filter(tags__0_1__name="test")

These indexes use 0-based indexing.

Nested ``EmbeddedModelArrayField``\s
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If your models use nested ``EmbeddedModelArrayField``\s, you can't use double
underscores to query into the the second level.

For example, if the ``Tag`` model had an ``EmbeddedModelArrayField`` called
``colors``:

    >>> Post.objects.filter(tags__colors__name="blue")
    ...
    ValueError: Cannot perform multiple levels of array traversal in a query.
