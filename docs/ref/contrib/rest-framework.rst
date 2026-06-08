==================================
Django REST Framework integration
==================================

Django MongoDB Backend provides serializer classes for using
`Django REST Framework`_ (DRF) with :class:`~django_mongodb_backend.models.EmbeddedModel`
fields.

.. _Django REST Framework: https://www.django-rest-framework.org/

Installation
============

Install the optional dependency::

    pip install "django-mongodb-backend[rest_framework]"

Add ``rest_framework`` to :setting:`INSTALLED_APPS`::

    INSTALLED_APPS = [
        ...
        "rest_framework",
    ]

Usage
=====

``EmbeddedModelSerializer``
---------------------------

Subclass :class:`~django_mongodb_backend.rest_framework.EmbeddedModelSerializer`
for each :class:`~django_mongodb_backend.models.EmbeddedModel` you want to
serialize. Set ``Meta.model`` and ``Meta.fields`` just like Django's
``ModelForm``::

    from django_mongodb_backend.rest_framework import EmbeddedModelSerializer

    class AddressSerializer(EmbeddedModelSerializer):
        class Meta:
            model = Address
            fields = "__all__"

Fields are auto-generated from the embedded model's field definitions:

* :class:`~django_mongodb_backend.fields.EmbeddedModelField` → nested
  ``EmbeddedModelSerializer`` (recursive)
* :class:`~django_mongodb_backend.fields.EmbeddedModelArrayField` → DRF
  ``ListSerializer`` wrapping a nested ``EmbeddedModelSerializer``
* :class:`~django_mongodb_backend.fields.ArrayField` → DRF ``ListField``
* All standard Django model fields → standard DRF fields

The primary key field is excluded automatically.

``to_internal_value()`` returns an ``EmbeddedModel`` instance rather than a
plain ``dict``, so the result integrates directly with the Django MongoDB
Backend ORM layer.

Saving is not supported directly on ``EmbeddedModelSerializer`` — embedded
models must be saved through their parent model.

``MongoModelSerializer``
------------------------

Subclass :class:`~django_mongodb_backend.rest_framework.MongoModelSerializer`
for regular Django models that contain MongoDB-specific fields::

    from django_mongodb_backend.rest_framework import MongoModelSerializer

    class BookSerializer(MongoModelSerializer):
        class Meta:
            model = Book
            fields = "__all__"

``MongoModelSerializer`` extends DRF's ``ModelSerializer`` and automatically
generates the correct DRF fields for:

* :class:`~django_mongodb_backend.fields.EmbeddedModelField`
* :class:`~django_mongodb_backend.fields.EmbeddedModelArrayField`
* :class:`~django_mongodb_backend.fields.ArrayField`
* :class:`~django_mongodb_backend.fields.PolymorphicEmbeddedModelField` (read-only)
* :class:`~django_mongodb_backend.fields.PolymorphicEmbeddedModelArrayField` (read-only)
* :class:`~django_mongodb_backend.fields.ObjectIdField`
* :class:`~django_mongodb_backend.fields.ObjectIdAutoField`

Explicit field declarations override the auto-generated ones::

    class BookSerializer(MongoModelSerializer):
        author = AuthorSerializer()  # override the auto-generated field

        class Meta:
            model = Book
            fields = "__all__"

Examples
========

Single embedded model field
----------------------------

::

    from django.db import models
    from django_mongodb_backend.fields import EmbeddedModelField
    from django_mongodb_backend.models import EmbeddedModel
    from django_mongodb_backend.rest_framework import (
        EmbeddedModelSerializer,
        MongoModelSerializer,
    )

    class Address(EmbeddedModel):
        city = models.CharField(max_length=100)
        zip_code = models.CharField(max_length=20)

    class Person(models.Model):
        name = models.CharField(max_length=100)
        address = EmbeddedModelField(Address)

    class AddressSerializer(EmbeddedModelSerializer):
        class Meta:
            model = Address
            fields = "__all__"

    class PersonSerializer(MongoModelSerializer):
        class Meta:
            model = Person
            fields = "__all__"

Serializing a ``Person`` instance::

    person = Person.objects.get(pk=...)
    data = PersonSerializer(person).data
    # data = {"id": "...", "name": "Alice", "address": {"city": "Berlin", "zip_code": "10115"}}

Deserializing and saving::

    serializer = PersonSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()

Array of embedded models
------------------------

::

    from django_mongodb_backend.fields import EmbeddedModelArrayField

    class Tag(EmbeddedModel):
        label = models.CharField(max_length=50)

    class Article(models.Model):
        title = models.CharField(max_length=200)
        tags = EmbeddedModelArrayField(Tag, null=True)

    class TagSerializer(EmbeddedModelSerializer):
        class Meta:
            model = Tag
            fields = "__all__"

    class ArticleSerializer(MongoModelSerializer):
        class Meta:
            model = Article
            fields = "__all__"

The ``tags`` field is represented as a JSON array of objects::

    # GET response body
    {"id": "...", "title": "Hello", "tags": [{"label": "python"}, {"label": "mongodb"}]}

Polymorphic embedded model fields
----------------------------------

:class:`~django_mongodb_backend.fields.PolymorphicEmbeddedModelField` and
:class:`~django_mongodb_backend.fields.PolymorphicEmbeddedModelArrayField`
are serialized automatically by
:class:`~django_mongodb_backend.rest_framework.PolymorphicEmbeddedModelSerializer`,
which dispatches to the correct concrete
:class:`~django_mongodb_backend.rest_framework.EmbeddedModelSerializer` based
on the runtime type of each instance::

    from django_mongodb_backend.fields import PolymorphicEmbeddedModelField
    from django_mongodb_backend.models import EmbeddedModel

    class Dog(EmbeddedModel):
        name = models.CharField(max_length=100)
        barks = models.BooleanField(default=True)

    class Cat(EmbeddedModel):
        name = models.CharField(max_length=100)
        purrs = models.BooleanField(default=True)

    class PetOwner(models.Model):
        name = models.CharField(max_length=100)
        pet = PolymorphicEmbeddedModelField([Dog, Cat], null=True)

    class PetOwnerSerializer(MongoModelSerializer):
        class Meta:
            model = PetOwner
            fields = "__all__"

Serializing a ``PetOwner`` with a ``Dog`` instance::

    owner = PetOwner.objects.get(pk=...)
    data = PetOwnerSerializer(owner).data
    # data = {"id": "...", "name": "Alice", "pet": {"name": "Rex", "barks": true}}

Because ``PolymorphicEmbeddedModelField`` is not editable, the serialized field
is read-only. To accept writes, declare the field manually on the serializer.
