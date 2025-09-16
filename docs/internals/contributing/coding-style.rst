============
Coding style
============

Please follow these coding standards when writing code.

.. _coding-style-pre-commit:

Pre-commit checks
=================

`pre-commit <https://pre-commit.com>`_ is a framework for managing pre-commit
hooks. These hooks help to identify simple issues before committing code for
review. By checking for these issues before code review it allows the reviewer
to focus on the change itself, and it can also help to reduce the number of CI
runs.

To use the tool, first install ``pre-commit`` and then the git hooks:

.. code-block:: bash

    $ python -m pip install pre-commit
    $ pre-commit install

On the first commit ``pre-commit`` will install the hooks, these are installed
in their own environments and will take a short while to install on the first
run. Subsequent checks will be significantly faster. If an error is found an
appropriate error message will be displayed. If the error was with ``ruff`` (a
tool to standardize code formatting), then it will go ahead and fix it for you.
Review the changes and re-stage for commit if you are happy with them.

.. seealso::

    The guidelines from Django's :ref:`Python style guide<coding-style-python>`
    are generally applicable.
