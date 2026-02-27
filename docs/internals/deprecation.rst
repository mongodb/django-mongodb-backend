====================
Deprecation Timeline
====================

This document outlines when various pieces of Django MongoDB Backend will be
removed or altered in a backward incompatible way, following their deprecation.

6.1
---

.. _inline-constraints-and-indexes-deprecation:

Inline constraints and indexes on embedded models
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Defining indexes and constraints on embedded models using ``unique=True``,
``db_index=True``, ``Meta.constraints``, and ``Meta.indexes`` will no longer
be supported. Instead, use
:class:`~django_mongodb_backend.indexes.EmbeddedFieldIndex` and
:class:`~django_mongodb_backend.constraints.EmbeddedFieldUniqueConstraint` on
the top-level model.

For example, instead of::

    class Target(EmbeddedModel):
        foo = models.IntegerField(unique=True)


    class MyModel(models.Model):
        field = EmbeddedModelField(Target)

use::

    from django_mongodb_backend.indexes import EmbeddedFieldUniqueConstraint


    class Target(EmbeddedModel):
        foo = models.IntegerField()


    class MyModel(models.Model):
        field = EmbeddedModelField(Target)

        class Meta:
            constraints = [
                EmbeddedFieldUniqueConstraint(fields=["field.foo"], name="..."),
            ]

6.0
---

.. _parse-uri-deprecation:

``parse_uri()`` will be removed
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``django_mongodb_backend.utils.parse_uri()`` is deprecated in favor of putting
the connection string in ``DATABASES["HOST"]``.

For example, instead of::

    DATABASES = {
        "default": django_mongodb_backend.parse_uri("mongodb://localhost:27017/", db_name="db"),
    }

use::

    DATABASES = {
        'default': {
            'ENGINE': 'django_mongodb_backend',
            'HOST': 'mongodb://localhost:27017/',
            'NAME': 'db',
        },
    }
