=============================================
Preparing for the next Django feature release
=============================================

This document explains how to prepare for the next feature of Django (currently
every 8 months). It includes how to rebase a branch of :ref:`the Django fork
<django-fork>` (``mongodb-forks/django``) onto its corresponding upstream
Django branch, resolve conflicts, and account for tests or features that
Django adds along the way.

The example below uses ``mongodb-6.1.x``, but the same steps apply to any of
the fork's branches.

Add the upstream remote
========================

If you haven't already, add ``django/django`` as a remote of your clone of
the Django fork:

.. code-block:: bash

    $ git remote add upstream https://github.com/django/django.git
    $ git fetch upstream

Choose the right upstream branch
=================================

Which upstream branch to rebase onto depends on where Django is in its
release cycle:

- Once Django creates a ``stable/X.Y.x`` branch for a release, rebase the
  matching ``mongodb-X.Y.x`` branch onto it, e.g. ``upstream/stable/6.1.x``.
- Before that branch exists — i.e. while the next feature release is still
  under development on ``main`` — rebase onto ``upstream/main`` instead.

.. admonition:: When is a new stable branch created?

    A new Django stable branch is created right before the alpha release, about
    2 ½ months before the final release; `see the Django 6.1 roadmap
    <https://www.djangoproject.com/download/6.1/roadmap/>`_. At that point, you
    should duplicate the ``mongodb-6.1.x`` branch of the Django fork as
    ``mongodb-6.2.x`` and start rebasing it on Django's ``main`` branch.

Rebase
======

.. code-block:: bash

    $ git checkout mongodb-6.1.x
    $ git rebase upstream/stable/6.1.x

If it applies cleanly, skip ahead to :ref:`handling-test-failures`. Otherwise,
Git stops at each conflicting commit for you to resolve.

Resolving conflicts
====================

Most conflicts happen because a patch commit in the fork modifies a test file
(to swap in
:class:`~django_mongodb_backend.fields.ObjectIdAutoField`, remove a
SQL-specific assertion, etc.) and upstream Django has since changed the same
lines, e.g. to add a new assertion or rename something the patch touches.

Resolve these the same way you would any rebase conflict — edit the file to
combine both changes, ``git add`` it, and ``git rebase --continue``.

Push the rebase
================

A rebase rewrites commit hashes, so a force push is required to update the
Django fork:

.. code-block:: bash

    $ git push origin mongodb-6.1.x --force

.. _handling-test-failures:

Handling test failures
======================

A clean (or now-resolved) rebase only means Git found no *textual* conflicts.
It doesn't mean the branch still passes on MongoDB: Django may have added new
features or tests that no patch commit touches, so Git has no reason to stop
and ask you about it.

After you complete the rebase of the Django fork, rebase the corresponding
Django MongoDB Backend branch (e.g. `for Django 6.1
<https://github.com/mongodb/django-mongodb-backend/pull/422>`_) on the latest
main and force push it.

Observe any failing tests. You may need to amend the Django fork:

- Amend an existing commit if the fix is in the same category (e.g. amend the
  commit titled "Remove/edit SQL assertions for MongoDB" if Django adds a new
  test with SQL assertions.)
- Remove commits if they are obsolete.
- Add new commits to fix new problems.

Or, you may need to amend the Django MongoDB Backend branch:

- Make all changes that are required to pass the test suite in the first commit
  "Update to Django X.Y".
- Then add commits that add support for new features or that replace
  moneypatches in Django MongoDB Backend with new Django APIs.
- Finally, add commits that remove support for
  Django MongoDB Backend features that have reached the end of their
  :doc:`deprecation cycle </internals/deprecation>`.
- After the new Django feature release is issued, don't squash commits when
  merging this!
