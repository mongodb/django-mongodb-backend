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
----------------------------

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
-------------------------

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
-----------------------------

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

    upstream Django     mongodb-forks/django    backend repo
    ---------------     -------------------    ------------

    stable/X.Y.x ─rebase─▶ mongodb-X.Y.x ─force-push─▶ branch pinned by ref:
                              │                        history rewritten
                              │ retrigger-ci
                              │ (ci_rerun entry)
                              ▼
                            backend CI
                              ├─ branch name: dispatch test workflows
                              │   on that ref
                              ├─ {"pr": N}: re-run the PR's workflow runs
                              └─ evergreen: true: retry the Evergreen patch
