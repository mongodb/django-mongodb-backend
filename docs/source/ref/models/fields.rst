Model field reference
=====================

.. module:: django_mongodb_backend.fields

Some MongoDB-specific fields are available in ``django_mongodb_backend.fields``.

``ArrayField``
--------------

.. class:: ArrayField(base_field, max_size=None, size=None, **options)

    A field for storing lists of data. Most field types can be used, and you
    pass another field instance as the :attr:`~ArrayField.base_field`. You may
    also specify a :attr:`~ArrayField.size` or :attr:`~ArrayField.max_size`.
    ``ArrayField`` can be nested to store multi-dimensional arrays.

    If you give the field a :attr:`~django.db.models.Field.default`, ensure
    it's a callable such as ``list`` (for an empty default) or a callable that
    returns a list (such as a function). Incorrectly using ``default=[]``
    creates a mutable default that is shared between all instances of
    ``ArrayField``.

    .. attribute:: base_field

        This is a required argument.

        Specifies the underlying data type and behavior for the array. It
        should be an instance of a subclass of
        :class:`~django.db.models.Field`. For example, it could be an
        :class:`~django.db.models.IntegerField` or a
        :class:`~django.db.models.CharField`. Most field types are permitted,
        with the exception of those handling relational data
        (:class:`~django.db.models.ForeignKey`,
        :class:`~django.db.models.OneToOneField` and
        :class:`~django.db.models.ManyToManyField`) and file fields (
        :class:`~django.db.models.FileField` and
        :class:`~django.db.models.ImageField`). :class:`EmbeddedModelField` is
        also not (yet) supported.

        It is possible to nest array fields - you can specify an instance of
        ``ArrayField`` as the ``base_field``. For example::

            from django.db import models
            from django_mongodb_backend.fields import ArrayField


            class ChessBoard(models.Model):
                board = ArrayField(
                    ArrayField(
                        models.CharField(max_length=10, blank=True),
                        size=8,
                    ),
                    size=8,
                )

        Transformation of values between the database and the model, validation
        of data and configuration, and serialization are all delegated to the
        underlying base field.

    .. attribute:: max_size

        This is an optional argument.

        If passed, the array will have a maximum size as specified, validated
        by forms and model validation, but not enforced by the database.

        The ``max_size`` and ``size`` options are mutually exclusive.

    .. attribute:: size

        This is an optional argument.

        If passed, the array will have size as specified, validated by forms
        and model validation, but not enforced by the database.

Querying ``ArrayField``
~~~~~~~~~~~~~~~~~~~~~~~

There are a number of custom lookups and transforms for :class:`ArrayField`.
We will use the following example model::

    from django.db import models
    from django_mongodb_backend.fields import ArrayField


    class Post(models.Model):
        name = models.CharField(max_length=200)
        tags = ArrayField(models.CharField(max_length=200), blank=True)

        def __str__(self):
            return self.name

.. fieldlookup:: arrayfield.contains

``contains``
^^^^^^^^^^^^

The :lookup:`contains` lookup is overridden on :class:`ArrayField`. The
returned objects will be those where the values passed are a subset of the
data. It uses the ``$setIntersection`` operator. For example:

.. code-block:: pycon

    >>> Post.objects.create(name="First post", tags=["thoughts", "django"])
    >>> Post.objects.create(name="Second post", tags=["thoughts"])
    >>> Post.objects.create(name="Third post", tags=["tutorial", "django"])

    >>> Post.objects.filter(tags__contains=["thoughts"])
    <QuerySet [<Post: First post>, <Post: Second post>]>

    >>> Post.objects.filter(tags__contains=["django"])
    <QuerySet [<Post: First post>, <Post: Third post>]>

    >>> Post.objects.filter(tags__contains=["django", "thoughts"])
    <QuerySet [<Post: First post>]>

``contained_by``
~~~~~~~~~~~~~~~~

This is the inverse of the :lookup:`contains <arrayfield.contains>` lookup -
the objects returned will be those where the data is a subset of the values
passed. It uses the ``$setIntersection`` operator. For example:

.. code-block:: pycon

    >>> Post.objects.create(name="First post", tags=["thoughts", "django"])
    >>> Post.objects.create(name="Second post", tags=["thoughts"])
    >>> Post.objects.create(name="Third post", tags=["tutorial", "django"])

    >>> Post.objects.filter(tags__contained_by=["thoughts", "django"])
    <QuerySet [<Post: First post>, <Post: Second post>]>

    >>> Post.objects.filter(tags__contained_by=["thoughts", "django", "tutorial"])
    <QuerySet [<Post: First post>, <Post: Second post>, <Post: Third post>]>

.. fieldlookup:: arrayfield.overlap

``overlap``
~~~~~~~~~~~

Returns objects where the data shares any results with the values passed. It
uses the ``$setIntersection`` operator. For example:

.. code-block:: pycon

    >>> Post.objects.create(name="First post", tags=["thoughts", "django"])
    >>> Post.objects.create(name="Second post", tags=["thoughts", "tutorial"])
    >>> Post.objects.create(name="Third post", tags=["tutorial", "django"])

    >>> Post.objects.filter(tags__overlap=["thoughts"])
    <QuerySet [<Post: First post>, <Post: Second post>]>

    >>> Post.objects.filter(tags__overlap=["thoughts", "tutorial"])
    <QuerySet [<Post: First post>, <Post: Second post>, <Post: Third post>]>

.. fieldlookup:: arrayfield.len

``len``
^^^^^^^

Returns the length of the array. The lookups available afterward are those
available for :class:`~django.db.models.IntegerField`. For example:

.. code-block:: pycon

    >>> Post.objects.create(name="First post", tags=["thoughts", "django"])
    >>> Post.objects.create(name="Second post", tags=["thoughts"])

    >>> Post.objects.filter(tags__len=1)
    <QuerySet [<Post: Second post>]>

.. fieldlookup:: arrayfield.index

Index transforms
^^^^^^^^^^^^^^^^

Index transforms index into the array. Any non-negative integer can be used.
There are no errors if it exceeds the :attr:`max_size <ArrayField.max_size>` of
the array. The lookups available after the transform are those from the
:attr:`base_field <ArrayField.base_field>`. For example:

.. code-block:: pycon

    >>> Post.objects.create(name="First post", tags=["thoughts", "django"])
    >>> Post.objects.create(name="Second post", tags=["thoughts"])

    >>> Post.objects.filter(tags__0="thoughts")
    <QuerySet [<Post: First post>, <Post: Second post>]>

    >>> Post.objects.filter(tags__1__iexact="Django")
    <QuerySet [<Post: First post>]>

    >>> Post.objects.filter(tags__276="javascript")
    <QuerySet []>

These indexes use 0-based indexing.

.. fieldlookup:: arrayfield.slice

Slice transforms
^^^^^^^^^^^^^^^^

Slice transforms take a slice of the array. Any two non-negative integers can
be used, separated by a single underscore. The lookups available after the
transform do not change. For example:

.. code-block:: pycon

    >>> Post.objects.create(name="First post", tags=["thoughts", "django"])
    >>> Post.objects.create(name="Second post", tags=["thoughts"])
    >>> Post.objects.create(name="Third post", tags=["django", "python", "thoughts"])

    >>> Post.objects.filter(tags__0_1=["thoughts"])
    <QuerySet [<Post: First post>, <Post: Second post>]>

    >>> Post.objects.filter(tags__0_2__contains=["thoughts"])
    <QuerySet [<Post: First post>, <Post: Second post>]>

These indexes use 0-based indexing.

``EmbeddedModelField``
----------------------

.. class:: EmbeddedModelField(embedded_model, **kwargs)

Stores a model of type ``embedded_model``.

    .. attribute:: embedded_model

        This is a required argument.

        Specifies the model class to embed. It must be a subclass of
        :class:`django_mongodb_backend.models.EmbeddedModel`.

        It can be either a concrete model class or a :ref:`lazy reference
        <lazy-relationships>` to a model class.

        The embedded model cannot have relational fields
        (:class:`~django.db.models.ForeignKey`,
        :class:`~django.db.models.OneToOneField` and
        :class:`~django.db.models.ManyToManyField`).

        It is possible to nest embedded models. For example::

            from django.db import models
            from django_mongodb_backend.fields import EmbeddedModelField
            from django_mongodb_backend.models import EmbeddedModel

            class Address(EmbeddedModel):
                ...

            class Author(EmbeddedModel):
                address = EmbeddedModelField(Address)

            class Book(models.Model):
                author = EmbeddedModelField(Author)

See :doc:`/topics/embedded-models` for more details and examples.

.. admonition:: Migrations support is limited

    :djadmin:`makemigrations` does not yet detect changes to embedded models.

    After you create a model with an ``EmbeddedModelField`` or add an
    ``EmbeddedModelField`` to an existing model, no further updates to the
    embedded model will be made. Using the models above as an example, if you
    created these models and then added an indexed field to ``Address``,
    the index created in the nested ``Book`` embed is not created.

``ObjectIdAutoField``
---------------------

.. class:: ObjectIdAutoField

This field is typically the default primary key field for all models stored in
MongoDB. See :ref:`specifying the-default-pk-field`.

``ObjectIdField``
-----------------

.. class:: ObjectIdField

Stores an :class:`~bson.objectid.ObjectId`.
