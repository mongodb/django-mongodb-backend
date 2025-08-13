==================
Performance tests
==================

Django MongoDB Backend uses a benchmarking suite to catch performance regressions.
This suite is located in the top-level ``performance_tests`` directory of the Django MongoDB Backend repository.
See the `specification <https://github.com/mongodb/specifications/blob/master/source/benchmarking/odm-benchmarking.md>`__
for detailed design and implementation decisions.

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
    $ mkdir performance_tests/odm-data
    $ cp specifications/source/benchmarking/odm-data/flat_models.tgz performance_tests/odm-data/flat_models.tgz
    $ cp specifications/source/benchmarking/odm-data/nested_models.tgz performance_tests/odm-data/nested_models.tgz
    $ pushd performance_tests/odm-data
    $ tar xf flat_models.tgz
    $ tar xf nested_models.tgz
    $ popd

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
