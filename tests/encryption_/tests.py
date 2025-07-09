from django.core import management
from django.db import connection
from django.test import TestCase, modify_settings

from django_mongodb_backend.encryption import get_auto_encryption_opts

from .models import Person


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
        with connection.schema_editor() as editor:
            self.assertEqual(editor._get_encrypted_fields_map(self.person), expected)


@modify_settings(
    INSTALLED_APPS={"prepend": "django_mongodb_backend"},
)
class AutoEncryptionOptsTests(TestCase):
    databases = {"default", "encrypted"}

    def test_auto_encryption_opts(self):
        management.call_command("get_encrypted_fields_map", verbosity=0)

    def test_requires_key_vault_namespace(self):
        with self.assertRaises(TypeError):
            # Should fail because `key_vault_namespace` is a required kwarg
            get_auto_encryption_opts()
