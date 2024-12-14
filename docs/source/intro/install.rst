=================================
Installing Django MongoDB Backend
=================================

Use the version of ``django-mongodb-backend`` that corresponds to your version
of Django. For example, to get the latest compatible release for Django 5.2.x:

.. code-block:: bash

    $ pip install --pre django-mongodb-backend==5.2.*

(Until the package is out of beta, you must use pip's ``--pre`` option.)

The minor release number of Django doesn't correspond to the minor release
number of ``django-mongodb-backend``. Use the latest minor release of each.

Next, you'll have to :doc:`configure your project <configure>`.
