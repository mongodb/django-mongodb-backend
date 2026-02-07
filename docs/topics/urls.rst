==============
URL dispatcher
==============

If you're unfamiliar with how URL patterns are defined in Django, you should
first read Django's documentation about its :doc:`django:topics/http/urls`.

.. _object-id-in-url-patterns:

Matching ``ObjectId``\s in URL patterns
=======================================

.. versionadded:: 6.0.3

Since primary key values are often included in URL patterns, Django MongoDB
Backend registers a :ref:`custom path converter
<django:registering-custom-path-converters>` named ``object_id`` to match
:class:`~bson.objectid.ObjectId`\s.

For example, you can write a pattern like this::

    from django.urls import path

    from . import views

    urlpatterns = [
        path("author/<object_id:pk>/", views.AuthorDetail.as_view()),
    ]

This example matches a URL like ``/author/69868bc49b827bee857500c2/`` and
``pk=ObjectId("69868bc49b827bee857500c2")`` will be available in the view's
keyword arguments.
