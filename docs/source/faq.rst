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
