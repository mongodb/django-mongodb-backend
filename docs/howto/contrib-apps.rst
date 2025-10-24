=================================
Configuring Django's contrib apps
=================================

Generally, Django's contrib apps work out of the box, but here are some
required adjustments.

Apps with models
================

Each contrib app that has models that use :class:`~django.db.models.AutoField`
(:mod:`~django.contrib.admin`, :mod:`~django.contrib.auth`,
:mod:`~django.contrib.contenttypes`, :mod:`~django.contrib.flatpages`,
:mod:`~django.contrib.redirects`, and :mod:`~django.contrib.sites`) must:

#. Be configured with an ``AppConfig`` that specifies
   ``default_auto_field = "django_mongodb_backend.fields.ObjectIdAutoField"``.
   See :ref:`specifying the-default-pk-field`.
#. Have migrations that use :class:`.ObjectIdAutoField`. See
   :ref:`configuring-migrations`.

``contrib.sites``
=================

Usually the :doc:`sites framework <django:ref/contrib/sites>` requires the
:setting:`SITE_ID` setting to be an integer corresponding to the primary key of
the :class:`~django.contrib.sites.models.Site` object. For MongoDB, however,
all primary keys are :class:`~bson.objectid.ObjectId`\s, and so
:setting:`SITE_ID` must be set accordingly::

    from bson import ObjectId

    SITE_ID = ObjectId("000000000000000000000001")

You must also use the :setting:`SILENCED_SYSTEM_CHECKS` setting to suppress
Django's system check requiring :setting:`SITE_ID` to be an integer::

    SILENCED_SYSTEM_CHECKS = [
        "sites.E101",  # SITE_ID must be an ObjectId for MongoDB.
    ]
