=================================
Configuring Django's contrib apps
=================================

Generally, Django's contribs app work out of the box, but here are some
required adjustments.

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
