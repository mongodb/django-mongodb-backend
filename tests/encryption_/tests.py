from django.db import connection
from django.test import TestCase

from .models import Person


class EncryptedModelTests(TestCase):
    databases = {"default", "encrypted"}

    @classmethod
    def setUpTestData(cls):
        cls.person = Person(ssn="123-45-6789")

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
