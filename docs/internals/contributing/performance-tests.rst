==================
Performance tests
==================

Django MongoDB Backend uses a benchmarking suite to catch performance regressions.
This suite is located in the top-level ``performance_tests`` directory of the Django MongoDB Backend repository.

.. _running-perf-tests:

Running the performance tests
==============================

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

Next, start :doc:`a local instance of mongod
<manual:tutorial/manage-mongodb-processes>`.

Then, set up the benchmark data:

.. code-block:: bash

    $ git clone --depth 1 https://github.com/mongodb/specifications.git
    $ pushd specifications/source/benchmarking/odm-data
    $ tar xf flat_models.tgz
    $ tar xf nested_models.tgz
    $ popd
    $ export DJANGO_MONGODB_PERFORMANCE_TEST_DATA_PATH="specifications/source/benchmarking/odm-data"
    $ export OUTPUT_FILE="results.json"

Finally, run the benchmarks themselves:

.. code-block:: bash

    $ cd performance_tests
    $ python manage.py test

.. warning::

    Running the full benchmark suite locally will take a significant amount of time.
    Use the ``FASTBENCH=1`` environment variable to run a shorter version of the benchmarks.

To run an individual benchmark:

.. code-block:: bash

    $ python manage.py test perftest.tests.TestLargeNestedDocFilterArray
