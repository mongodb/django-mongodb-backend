=====
Admin
=====

Django MongoDB Backend supports the Django admin interface. To enable it, ensure
that you have :ref:`specified the default pk field
<specifying the-default-pk-field>` for the
:class:`~django.contrib.admin.apps.AdminConfig` class as described in the
:doc:`Getting Started </intro/configure>` guide.

``EncryptedModelAdmin``
=======================

.. class:: EncryptedModelAdmin

    .. versionadded:: 5.2.3

    A :class:`~django.contrib.admin.ModelAdmin` subclass that supports models
    with encrypted fields. Use this class as a base class for your model's admin
    class to ensure that encrypted fields are handled correctly in the admin
    interface.

    Register encrypted models with the Django admin using the
    ``EncryptedModelAdmin`` as shown below::

        # myapp/admin.py
        from django.contrib import admin
        from django_mongodb_backend.admin import EncryptedModelAdmin
        from .models import Patient


        @admin.register(Patient)
        class PatientAdmin(EncryptedModelAdmin):
            pass
