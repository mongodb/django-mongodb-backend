from django.core import management
from django.db import connections
from django.test import TestCase, modify_settings, override_settings

from django_mongodb_backend import encryption

from .models import Person
from .routers import TestEncryptedRouter


@modify_settings(
    INSTALLED_APPS={"prepend": "django_mongodb_backend"},
)
@override_settings(DATABASE_ROUTERS=[TestEncryptedRouter()])
class EncryptedModelTests(TestCase):
    databases = {"default", "encrypted"}

    @classmethod
    def setUpTestData(cls):
        cls.person = Person(ssn="123-45-6789")
        cls.person.save()

    def test_encrypted_fields_map(self):
        """ """
        expected = {
            "fields": [
                {
                    "path": "ssn",
                    "bsonType": "string",
                    "queries": [{"contention": 1, "queryType": "equality"}],
                }
            ]
        }
        with connections["encrypted"].schema_editor() as editor:
            self.assertEqual(editor._get_encrypted_fields_map(self.person), expected)

    def test_auto_encryption_opts(self):
        management.call_command(
            "get_encrypted_fields_map", "--database", self.person._meta.model.db_name, verbosity=0
        )

    def test_requires_key_vault_namespace(self):
        with self.assertRaisesMessage(
            TypeError,
            expected_message="get_auto_encryption_opts() missing 1 required"
            " keyword-only argument: 'key_vault_namespace'",
        ):
            encryption.get_auto_encryption_opts()
