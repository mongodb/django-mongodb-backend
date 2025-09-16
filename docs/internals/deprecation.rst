====================
Deprecation Timeline
====================

This document outlines when various pieces of Django MongoDB Backend will be
removed or altered in a backward incompatible way, following their deprecation.

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
