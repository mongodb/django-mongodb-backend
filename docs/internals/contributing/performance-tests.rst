=================
Performance tests
=================

Django MongoDB Backend uses a benchmarking suite to catch performance
regressions.

See the `ODM Performance Benchmarking specification
<https://github.com/mongodb/specifications/blob/master/source/benchmarking/odm-benchmarking.md>`__
for an overview of design and implementation decisions.

.. _running-perf-tests:

Running the performance tests
=============================

First, :ref:`setup your environment to run the unit tests<running-unit-tests>`.

Then, set up the benchmark data, running the following commands from the
``django-mongodb-backend`` repository's root directory::

.. code-block:: bash

    $ git clone --depth 1 https://github.com/mongodb/specifications.git
    $ mkdir performance_tests/odm-data
    $ cp specifications/source/benchmarking/odm-data/flat_models.tgz performance_tests/odm-data/flat_models.tgz
    $ cp specifications/source/benchmarking/odm-data/nested_models.tgz performance_tests/odm-data/nested_models.tgz
    $ pushd performance_tests/odm-data
    $ tar xf flat_models.tgz
    $ tar xf nested_models.tgz
    $ popd

To run the benchmarks:

.. code-block:: bash

    $ cd performance_tests
    $ FASTBENCH=1 ./runtests.py

.. warning::

    Running the full benchmark suite without ``FASTBENCH=1`` will take a
    significant amount of time.

To run an individual benchmark (again, you may want to add ``FASTBENCH=1``):

.. code-block:: bash

    $ ./runtests.py perf.tests.TestLargeNestedDocFilterArray
