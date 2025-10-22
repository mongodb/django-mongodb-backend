===============
Release process
===============

.. _supported-versions-policy:

Supported versions
==================

Django MongoDB Backend follows Django's :ref:`supported versions policy
<django:supported-versions-policy>`.

The main development branch of Django MongoDB Backend follows the most recent
:term:`django:feature release` of Django and gets all new features and
non-critical bug fixes.

Security fixes and data loss bugs will also be applied to the previous feature
release branch, and any other supported long-term support release branches.

As a concrete example, consider a moment in time between the release of Django
5.2 and 6.0. At this point in time:

- Features will be added to the main branch, to be released as Django 5.2.x.

- Critical bug fixes will also be applied to the 5.1.x branch and released as
  5.1.x, 5.1.x+1, etc.

- Security fixes and bug fixes for data loss issues will be applied to main,
  5.1.x, and any active LTS branches (e.g. 4.2.x, if Django MongoDB Backend
  supported it). They will trigger the release of 5.2.x, 5.1.y, 4.2.z.

.. _branch-policy:

Branch policy
=============

After a new Django :term:`django:feature release` (5.2, 6.0, 6.1 etc.), Django
MongoDB Backend's main branch starts tracking the new version following the
merge of a "Add support for Django X.Y" pull request. Before merging that pull
request, a branch is created off of main to track the previous feature release.
For example, the 5.1.x branch is created shortly after the release of Django
5.2, and main starts tracking the Django 5.2.x series.

Release
=======

Django MongoDB Backend uses GitHub Actions to publish new releases to PyPI. To
publish a new release to PyPI:

- Bump the version number in ``django_mongodb_backend/__init__.py``
  according to :ref:`the supported versions policy
  <supported-versions-policy>`.

- Update the release notes in ``docs/releases/#.#.x.rst`` for the new version.

- Run the ``Release`` workflow on GitHub Actions, optionally providing the new
  (dev) version number as input. E.g. ``5.2.3.dev0`` for a new development
  release after ``5.2.2``. (The workflow defaults to incrementing the
  version automatically.)

  - First run with ``Dry Run?`` selected and check test PyPI to ensure that
    ``pip install`` works as expected.

  - Then run without ``Dry Run?`` to publish the release to PyPI.

- Announce the new release on the relevant communication channels.
