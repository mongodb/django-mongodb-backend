=====================
Model field reference
=====================

Supported model fields
======================

All of Django's :doc:`model fields <django:ref/models/fields>` are
supported, except:

- :class:`~django.db.models.AutoField` (including
  :class:`~django.db.models.BigAutoField` and
  :class:`~django.db.models.SmallAutoField`)
- :class:`~django.db.models.CompositePrimaryKey`
- :class:`~django.db.models.GeneratedField`

A few notes about some of the other fields:

- :class:`~django.db.models.DateTimeField` is limited to millisecond precision
  (rather than microsecond like most other databases), and correspondingly,
  :class:`~django.db.models.DurationField` stores milliseconds rather than
  microseconds.
- :class:`~django.db.models.SmallIntegerField` and
  :class:`~django.db.models.PositiveSmallIntegerField` support 32 bit values
  (ranges ``(-2147483648, 2147483647)`` and ``(0, 2147483647)``, respectively),
  validated by forms and model validation. Be careful because MongoDB doesn't
  prohibit inserting values outside of the supported range and unique
  constraints don't work for values outside of the 32-bit range of the BSON
  ``int`` type.
- :class:`~django.db.models.IntegerField`,
  :class:`~django.db.models.BigIntegerField` and
  :class:`~django.db.models.PositiveSmallIntegerField`, and
  :class:`~django.db.models.PositiveBigIntegerField` support 64 bit values
  (ranges ``(-9223372036854775808, 9223372036854775807)`` and
  ``(0, 9223372036854775807)``, respectively), validated by forms and model
  validation. If you're inserting data outside of the ORM, you must cast all
  values to :class:`bson.int64.Int64`, otherwise values less then 32 bits will
  be stored as ``int`` and won't be validated by unique constraints.
- Similarly, all :class:`~django.db.models.DurationField` values are stored as
  :class:`bson.int64.Int64`.

MongoDB-specific model fields
=============================

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
        :class:`~django.db.models.ImageField`). For
        :class:`EmbeddedModelField`, use :class:`EmbeddedModelArrayField`.

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

.. fieldlookup:: mongo-arrayfield.contains

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

.. fieldlookup:: mongo-arrayfield.overlap

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

.. fieldlookup:: mongo-arrayfield.len

``len``
^^^^^^^

Returns the length of the array. The lookups available afterward are those
available for :class:`~django.db.models.IntegerField`. For example:

.. code-block:: pycon

    >>> Post.objects.create(name="First post", tags=["thoughts", "django"])
    >>> Post.objects.create(name="Second post", tags=["thoughts"])

    >>> Post.objects.filter(tags__len=1)
    <QuerySet [<Post: Second post>]>

.. fieldlookup:: mongo-arrayfield.index

Index transforms
^^^^^^^^^^^^^^^^

Index transforms index into the array. Any non-negative integer can be used.
There are no errors if it exceeds the :attr:`~ArrayField.max_size` of the
array. The lookups available after the transform are those from the
:attr:`~ArrayField.base_field`. For example:

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

.. fieldlookup:: mongo-arrayfield.slice

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

    See :ref:`the embedded model topic guide <embedded-model-field-example>`
    for more details and examples.

.. admonition:: Migrations support is limited

    :djadmin:`makemigrations` does not yet detect changes to embedded models.

    After you create a model with an ``EmbeddedModelField`` or add an
    ``EmbeddedModelField`` to an existing model, no further updates to the
    embedded model will be made. Using the models above as an example, if you
    created these models and then added an indexed field to ``Address``,
    the index created in the nested ``Book`` embed is not created.

``EmbeddedModelArrayField``
---------------------------

.. class:: EmbeddedModelArrayField(embedded_model, max_size=None, **kwargs)

    .. versionadded:: 5.2.0b1

    Similar to :class:`EmbeddedModelField`, but stores a **list** of models of
    type ``embedded_model`` rather than a single instance.

    .. attribute:: embedded_model

        This is a required argument that works just like
        :attr:`EmbeddedModelField.embedded_model`.

    .. attribute:: max_size

        This is an optional argument.

        If passed, the list will have a maximum size as specified, validated
        by forms and model validation, but not enforced by the database.

    See :ref:`the embedded model topic guide
    <embedded-model-array-field-example>` for more details and examples.

.. admonition:: Migrations support is limited

    As described above for :class:`EmbeddedModelField`,
    :djadmin:`makemigrations` does not yet detect changes to embedded models.

``ObjectIdAutoField``
---------------------

.. class:: ObjectIdAutoField

    This field is typically the default primary key field for all models stored
    in MongoDB. See :ref:`specifying the-default-pk-field`.

``ObjectIdField``
-----------------

.. class:: ObjectIdField

    Stores an :class:`~bson.objectid.ObjectId`.

``PolymorphicEmbeddedModelField``
---------------------------------

.. class:: PolymorphicEmbeddedModelField(embedded_models, **kwargs)

    .. versionadded:: 5.2.0b2

    Stores a model of one of the types in ``embedded_models``.

    .. attribute:: embedded_models

        This is a required argument that specifies a list of model classes
        that may be embedded.

        Each model class reference works just like
        :attr:`.EmbeddedModelField.embedded_model`.

    See :ref:`the embedded model topic guide
    <polymorphic-embedded-model-field-example>` for more details and examples.

.. admonition:: Migrations support is limited

    :djadmin:`makemigrations` does not yet detect changes to embedded models,
    nor does it create indexes or constraints for embedded models referenced
    by ``PolymorphicEmbeddedModelField``.

.. admonition:: Forms are not supported

    ``PolymorphicEmbeddedModelField``\s don't appear in model forms.

``PolymorphicEmbeddedModelArrayField``
--------------------------------------

.. class:: PolymorphicEmbeddedModelArrayField(embedded_models, **kwargs)

    .. versionadded:: 5.2.0b2

    Similar to :class:`PolymorphicEmbeddedModelField`, but stores a **list** of
    models of type ``embedded_models`` rather than a single instance.

    .. attribute:: embedded_models

        This is a required argument that works just like
        :attr:`PolymorphicEmbeddedModelField.embedded_models`.

    .. attribute:: max_size

        This is an optional argument.

        If passed, the list will have a maximum size as specified, validated
        by forms and model validation, but not enforced by the database.

    See :ref:`the embedded model topic guide
    <polymorphic-embedded-model-array-field-example>` for more details and
    examples.

.. admonition:: Migrations support is limited

    :djadmin:`makemigrations` does not yet detect changes to embedded models,
    nor does it create indexes or constraints for embedded models referenced
    by ``PolymorphicEmbeddedModelArrayField``.

.. admonition:: Forms are not supported

    ``PolymorphicEmbeddedModelArrayField``\s don't appear in model forms.
