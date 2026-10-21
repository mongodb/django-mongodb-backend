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

Handling backports
==================

If a bug fix on ``main`` should be applied to one or more stable branches
according to the :ref:`Supported versions policy <supported-versions-policy>`,
note it in the pull request description. Whoever merges the PR to ``main`` is
responsible for opening the backport PR against the stable branch(es). Prefix
the PR title with the branch name (e.g. ``[5.2.x] ...``).

.. _django-fork:

The Django fork
===============

Since Django's test suite is designed for SQL backends, running the tests with
Django MongoDB Backend requires some modifications that can't be incorporated
upstream such as:

- Modifying test models to use
  :class:`~django_mongodb_backend.fields.ObjectIdAutoField` instead of
  :class:`~django.db.models.AutoField`.
- Modify URL patterns and tests that assume an integer primary key to work with
  an :class:`~bson.objectid.ObjectId`.
- Removing or modifying SQL-specific assertions.

These changes are maintained in a `fork of Django
<https://github.com/mongodb-forks/django/>`_. Each Django feature release has a
corresponding branch in the fork. For example, for Django 6.0, the branch is
``mongodb-6.0.x``.

Periodically, each branch is rebased on the upstream Django branch to pickup
the latest changes. For example, ``mongodb-6.0.x`` is rebased on Django's
``stable/6.0.x`` branch.

During the development of the next Django feature release, the fork's
corresponding branch is rebased on Django's ``main`` branch. For example,
during the development of Django X.Y, ``mongodb-X.Y.x`` is rebased on Django's
``main`` branch. That branch is used in the "Update to Django X.Y" pull request
to be merged upon the release of Django X.Y.

Branch relationship summary
===========================

To summarize the relationship of each repositories' branches:

==============  =======================  ===============  ===============
Django version  Django MongoDB Backend   Django fork      Django upstream
==============  =======================  ===============  ===============
next (X.Y)      update PR                mongodb-X.Y.x    main
X.Y-1.x         main                     mongodb-X.Y-1.x  stable/X.Y-1.x
X.Y-2.x         X.Y-2.x                  mongodb-X.Y-2.x  stable/X.Y-2.x
==============  =======================  ===============  ===============

"next (X.Y)" is the feature release under development, e.g. 6.2 while Django
6.2 is unreleased. "X.Y-1.x" is the previous feature release series (e.g.
6.1.x), and "X.Y-2.x" the one before it (e.g. 6.0.x).

"update PR" is the open "Update to Django X.Y" pull request, e.g. `"Add
support for Django 6.2"
<https://github.com/mongodb/django-mongodb-backend/pulls>`_. When Django cuts
``stable/X.Y.x``, a new row is added for the next version and the previous
row's fork branch is repointed to the new stable branch.

Upstream sync automation
========================

A scheduled workflow in the fork, `upstream-sync.yml
<https://github.com/mongodb-forks/django/blob/master/.github/workflows/upstream-sync.yml>`_,
keeps each ``mongodb-X.Y.x`` branch current. It runs daily at 09:00 UTC. It
can also be run manually.

For each fork branch listed in the workflow's matrix, the workflow:

1. Rebases the branch onto the upstream branch (``main`` or ``stable/X.Y.x``).
2. Force-pushes the rebased branch.
3. Triggers the backend's CI (see below).

A rebase that conflicts is aborted. The workflow then opens an issue in the
fork for manual resolution. A rejected force-push also opens an issue.

CI trigger after a force-push
================================

The backend pins fork branches by ref. A force-push rewrites the branch
history, so the backend builds against new code, but no event tells the
backend. After a successful force-push, the workflow calls the `retrigger-ci
action
<https://github.com/mongodb-labs/drivers-github-tools/tree/main/retrigger-ci>`_
from drivers-github-tools to re-run the backend's CI.

The workflow's matrix maps each fork branch to a ``ci_rerun`` entry, which
selects one of these kinds:

- a branch name, e.g. ``main`` or ``6.0.x`` — dispatch the backend's test
  workflows on that branch,
- ``{"pr": N}`` — re-run the workflow runs of that pull request,
- ``"evergreen": true`` (combined with ``{"pr": N}``) — also retry the
  Evergreen patch.

The mapping is kept identical to the one the local sync tooling uses, so the
two cannot drift.

.. code-block:: text

    upstream Django         mongodb-forks/django            django-mongodb-backend
    ---------------         -------------------            -----------------------

    stable/X.Y.x ─ rebase ─▶ mongodb-X.Y.x
                                │
                                │ force-push (history rewritten)
                                ▼
                              mongodb-X.Y.x ── retrigger-ci ─▶ backend CI
                                                                │
                              ci_rerun entry:                   ├─ branch name
                              dispatch test workflows ─────────┤   on that ref
                                                                ├─ {"pr": N}
                              re-run PR workflow runs ──────────┤
                                                                └─ evergreen: true
                              retry Evergreen patch ────────────┘
