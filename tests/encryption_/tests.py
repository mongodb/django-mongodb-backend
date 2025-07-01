from django.db import connection
from django.test import TestCase

from .models import Person


class EncryptedModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.person = Person(ssn="123-45-6789")

    def test_encrypted_fields_map_on_instance(self):
        expected = {
            "fields": {
                "ssn": "EncryptedCharField",
            }
        }
        with connection.schema_editor() as editor:
            self.assertEqual(editor._get_encrypted_fields_map(self.person), expected)

    def test_non_encrypted_fields_not_included(self):
        with connection.schema_editor() as editor:
            encrypted_field_names = editor._get_encrypted_fields_map(self.person).get("fields")
            self.assertNotIn("name", encrypted_field_names)
