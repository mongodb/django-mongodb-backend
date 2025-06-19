===
FAQ
===

This page contains a list of some frequently asked questions.

Performance
===========

Querying across relational fields like :class:`~django.db.models.ForeignKey` and :class:`~django.db.models.ManyToManyField` is really slow. Is there a way to improve the speed of these joins?
-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

Not really. Joins use MongoDB's :doc:`$lookup
<manual:reference/operator/aggregation/lookup>` operator, which doesn't perform
well with large tables.

The best practice for modeling relational data in MongoDB is to instead use
:doc:`embedded models <topics/embedded-models>`.

Troubleshooting
===============

Debug logging
-------------

To troubleshoot MongoDB connectivity issues, you can enable :doc:`PyMongo's
logging <pymongo:examples/logging>` using :doc:`Django's LOGGING setting
<django:topics/logging>`.

This is a minimal :setting:`LOGGING` setting that enables PyMongo's ``DEBUG``
logging::

    LOGGING = {
        "version": 1,
        "disable_existing_loggers": False,
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
            },
        },
        "loggers": {
            "pymongo": {
                "handlers": ["console"],
                "level": "DEBUG",
            },
        },
    }

``dumpdata`` fails with ``CommandError: Unable to serialize database``
----------------------------------------------------------------------

If running ``manage.py dumpdata`` results in ``CommandError: Unable to
serialize database: 'EmbeddedModelManager' object has no attribute using'``,
see :ref:`configuring-database-routers-setting`.
