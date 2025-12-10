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

MongoDB version support policy
==============================

Major versions of MongoDB have an end-of-life date and are supported for three
years beyond that through the `MongoDB Extended Lifecycle Support Add-On
<https://www.mongodb.com/services/support/enterprise-advanced-support-plans>`_.

The goal of the Django MongoDB Backend MongoDB version support policy is to
ensure a supported version of Django is available through each MongoDB
version's extended lifecycle.

The last version of Django to support a given version of MongoDB corresponds to
the long-term support release of Django whose support extends approximately
three years after the MongoDB version's end-of-life date.

For example, MongoDB 6.0 reached its end-of-life on July 31, 2025 which means
its end of extended lifecycle support is July 2028. Since Django 5.2 LTS is
supported until April 2028 (within a few months of July 2028), it's the last
version of Django to support MongoDB 6.0.

.. csv-table::
    :header: "Django release series", "Supported MongoDB versions"

    "6.0", "7.0, 8.0"
    "5.2 LTS", "6.0, 7.0, 8.0"

.. seealso::

    * `Django Supported Versions
      <https://www.djangoproject.com/download/#supported-versions>`_
    * `MongoDB Software Lifecycle Schedules
      <https://www.mongodb.com/legal/support-policy/lifecycles>`_

.. _branch-policy:

Branch policy
=============

After a new Django :term:`django:feature release` (5.2, 6.0, 6.1 etc.), Django
MongoDB Backend's main branch starts tracking the new version following the
merge of a "Add support for Django X.Y" pull request. Before merging that pull
request, a branch is created off of main to track the previous feature release.
For example, the 5.1.x branch is created shortly after the release of Django
5.2, and main starts tracking the Django 5.2.x series.
