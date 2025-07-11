from django.core import management
from django.core.exceptions import ImproperlyConfigured
from django.db import connections
from django.test import TestCase, modify_settings, override_settings

from django_mongodb_backend import encryption

from .models import Patient
from .routers import TestEncryptedRouter


@modify_settings(
    INSTALLED_APPS={"prepend": "django_mongodb_backend"},
)
@override_settings(DATABASE_ROUTERS=[TestEncryptedRouter()])
class EncryptedModelTests(TestCase):
    databases = {"default", "encrypted"}

    @classmethod
    def setUpTestData(cls):
        cls.patient = Patient(ssn="123-45-6789")
        cls.patient.save()

    def test_encrypted_fields_map(self):
        """ """
        expected = {
            "fields": [
                {
                    "path": "ssn",
                    "bsonType": "string",
                    "queries": {"contention": 1, "queryType": "equality"},
                }
            ]
        }
        with connections["encrypted"].schema_editor() as editor:
            self.assertEqual(editor._get_encrypted_fields_map(self.patient), expected)

    def test_auto_encryption_opts(self):
        management.call_command(
            "get_encrypted_fields_map", "--database", self.patient._meta.model.db_name, verbosity=0
        )

    def test_requires_key_vault_namespace(self):
        with self.assertRaisesMessage(
            TypeError,
            expected_message="get_auto_encryption_opts() missing 1 required"
            " keyword-only argument: 'key_vault_namespace'",
        ):
            encryption.get_auto_encryption_opts()

    @override_settings(KMS_PROVIDER=None)
    def test_kms_provider_not_found(self):
        with self.assertRaisesMessage(
            ImproperlyConfigured,
            expected_message="No KMS_PROVIDER found. Please configure KMS_PROVIDER in settings.",
        ):
            connections["encrypted"].schema_editor().create_model(Patient)
