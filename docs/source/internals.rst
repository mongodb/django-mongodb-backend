=================
Project internals
=================

Documentation for people working on Django MongoDB Backend itself. This is the
place to go if you'd like to help improve Django MongoDB Backend or learn about
how the project is managed.

.. _issue-tracker:

Issue tracker
=============

To report a bug or to request a new feature in Django MongoDB Backend, please
open an issue in our issue tracker, JIRA:

1. Create a `JIRA account <https://jira.mongodb.org/>`_.

2. Navigate to the `Python Integrations project
   <https://jira.mongodb.org/projects/INTPYTHON/>`_.

3. Click **Create Issue**. Please provide as much information as possible about
   the issue and the steps to reproduce it.

Bug reports in JIRA for this project can be viewed by everyone.

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
