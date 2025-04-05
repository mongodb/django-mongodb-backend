==========
Unit tests
==========

Django MongoDB Backend uses the Django test suite, located in
``django-repo/tests``, as well as additional tests of its own, located in the
``tests`` directory of the Django MongoDB Backend repository.

The tests use the testing infrastructure that ships with Django. See
:doc:`django:topics/testing/overview` for an explanation of how to write new
tests.

.. _running-unit-tests:

Running the unit tests
======================

First, `fork Django MongoDB Backend on GitHub
<https://github.com/mongodb/django-mongodb-backend/fork>`__.

Second, create and activate a Python virtual environment:

.. code-block:: bash

    $ python -m venv .venv
    $ source .venv/bin/activate

Third, clone your fork and install it:

.. code-block:: bash

    $ git clone https://github.com/YourGitHubName/django-mongodb-backend.git
    $ cd django-mongodb-backend
    $ pip install -e .

Next, get and install a copy of MongoDB's Django fork. This fork has some
test suite adaptions for Django MongoDB Backend. There is a branch for each
feature release of Django (e.g. ``mongodb-6.0.x`` below).

.. code-block:: bash

   $ git clone https://github.com/mongodb-forks/django.git django-repo
   $ cd django-repo
   $ git checkout -t origin/mongodb-6.0.x
   $ python -m pip install -e .
   $ python -m pip install -r tests/requirements/py3.txt

Next, start :doc:`a local instance of mongod
<manual:tutorial/manage-mongodb-processes>`.

Then, create a test settings file, ``django-repo/tests/test_mongo.py``::

    from test_sqlite import *

    DATABASES = {
        "default": {
            "ENGINE": "django_mongodb_backend",
            "NAME": "django",
            # Needed if connecting to the Atlas test VM.
            "OPTIONS": {"directConnection": True},
        },
        "other": {
            "ENGINE": "django_mongodb_backend",
            "NAME": "django1",
            "OPTIONS": {"directConnection": True},
        },
    }

    DATABASE_ROUTERS = ["django_mongodb_backend.routers.MongoRouter"]
    DEFAULT_AUTO_FIELD = "django_mongodb_backend.fields.ObjectIdAutoField"

Finally, you can run the test script in the Django repository:

   $ ./tests/runtests.py --settings=test_mongo basic

This runs the tests in ``django-repo/tests/basic``. You can also specify a
directory in ``django-mongodb-backend/tests``. All of these directories
have an underscore suffix (e.g. ``queries_``) to distinguish them from Django's
own test directories.

.. warning::

    Don't try to invoke ``runtests.py`` without specifying any test apps
    (directories) as running all the tests at once will take hours.

.. seealso::

    :doc:`Django's guide to running its test suite
    <django:internals/contributing/writing-code/unit-tests>`.
