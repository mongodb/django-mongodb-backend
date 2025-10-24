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

    Define a model with encrypted fields:

    .. code-block:: python

        # myapp/models.py
        from django.db import models
        from django_mongodb_backend.fields import EmbeddedModelField


        class Patient(models.Model):
            patient_name = models.CharField(max_length=255)
            patient_id = models.BigIntegerField()
            patient_record = EmbeddedModelField("PatientRecord")

            def __str__(self):
                return f"{self.patient_name} ({self.patient_id})"

    Register it with the Django admin using the ``EncryptedModelAdmin`` as shown
    below:

    .. code-block:: python

        # myapp/admin.py
        from django.contrib import admin
        from django_mongodb_backend.admin import EncryptedModelAdmin
        from .models import Patient


        @admin.register(Patient)
        class PatientAdmin(EncryptedModelAdmin):
            pass
