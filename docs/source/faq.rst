===
FAQ
===

This page contains a list of some frequently asked questions.

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
