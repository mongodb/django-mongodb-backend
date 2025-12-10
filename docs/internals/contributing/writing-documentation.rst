=====================
Writing documentation
=====================

The documentation uses the `Sphinx <https://www.sphinx-doc.org/>`_
documentation system.

How the documentation is organized
==================================

The documentation is organized into several categories:

* :doc:`Tutorials </intro/index>` take the reader by the hand through a series
  of steps to create something.

  The important thing in a tutorial is to help the reader achieve something
  useful, preferably as early as possible, in order to give them confidence.

  Explain the nature of the problem we're solving, so that the reader
  understands what we're trying to achieve. Don't feel that you need to begin
  with explanations of how things work - what matters is what the reader does,
  not what you explain. It can be helpful to refer back to what you've done and
  explain afterward.

* :doc:`Topic guides </topics/index>` aim to explain a concept or subject at a
  fairly high level.

  Link to reference material rather than repeat it. Use examples and don't be
  reluctant to explain things that seem very basic to you - it might be the
  explanation someone else needs.

  Providing background context helps a newcomer connect the topic to things
  that they already know.

* :doc:`Reference guides </ref/index>` contain technical references for APIs.
  They describe the functioning of Django MongoDB Backend's internal machinery
  and instruct in its use.

  Keep reference material tightly focused on the subject. Assume that the
  reader already understands the basic concepts involved but needs to know or
  be reminded of how Django MongoDB Backend does it.

  Reference guides aren't the place for general explanation. If you find
  yourself explaining basic concepts, you may want to move that material to a
  topic guide.

* :doc:`How-to guides </howto/index>` are recipes that take the reader through
  steps in key subjects.

  What matters most in a how-to guide is what a user wants to achieve.
  A how-to should always be result-oriented rather than focused on internal
  details of how Django MongoDB Backend implements whatever is being discussed.

  These guides are more advanced than tutorials and assume some knowledge about
  how Django MongoDB Backendo works.

How to start contributing documentation
=======================================

Clone the Django repository to your local machine
-------------------------------------------------

If you'd like to start contributing to the docs, get the source code
repository:

.. code-block:: bash

     $ git clone https://github.com/mongodb/django-mongodb-backend.git

If you're planning to submit these changes, you might find it useful to make a
fork of this repository and clone your fork instead.

Set up a virtual environment and install dependencies
-----------------------------------------------------

Create and activate a virtual environment, then install the dependencies:

.. code-block:: bash

     $ python -m venv .venv
     $ source .venv/bin/activate
     $ python -m pip install -e ".[docs]"

Build the documentation locally
-------------------------------

You build the HTML output from the ``docs`` directory:

.. code-block:: bash

     $ cd docs
     $ make html

Your locally-built documentation will be accessible at
``_build/html/index.html`` and it can be viewed in any web browser.

Making edits to the documentation
---------------------------------

The source files are ``.rst`` files located in the ``docs/`` directory.

These files are written in the reStructuredText markup language. To learn the
markup, see the :ref:`reStructuredText reference <sphinx:rst-index>`.

To edit this page, for example, edit the file
``docs/internals/contributing/writing-documentation.txt`` and rebuild the
HTML with ``make html``.
