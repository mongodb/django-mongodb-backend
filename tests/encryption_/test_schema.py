from django.db import connections

from .models import Patient
from .test_base import QueryableEncryptionTestCase


class SchemaTests(QueryableEncryptionTestCase):
    maxDiff = None

    def test_get_encrypted_fields(self):
        """
        Test class method called by schema editor and management command to get
        encrypted fields for `create_collection` and `auto_encryption_opts`
        respectively.

        This method is called per collection when creating a new collection and
        per database when setting up auto encryption options.

        Data keys are not tested here as they are expected to differ each time.
        """
        expected_encrypted_fields = {
            "fields": [
                {
                    "bsonType": "long",
                    "path": "patient_id",
                    "queries": {"queryType": "equality"},
                },
                {
                    "bsonType": "string",
                    "path": "full_name",
                },
                {
                    "bsonType": "string",
                    "path": "notes",
                    "queries": {"queryType": "equality"},
                },
                {
                    "bsonType": "date",
                    "path": "registration_date",
                    "queries": {"queryType": "equality"},
                },
                {
                    "bsonType": "bool",
                    "path": "is_active",
                    "queries": {"queryType": "equality"},
                },
                {
                    "bsonType": "string",
                    "path": "contact_email",
                    "queries": {"queryType": "equality"},
                },
            ]
        }
        connection = connections["encrypted"]
        with connection.schema_editor() as editor:
            client = connection.connection
            encrypted_fields = editor._get_encrypted_fields(Patient, client)
            for field in encrypted_fields["fields"]:
                # Remove data keys from the output; they are expected to differ
                field.pop("keyId", None)
            self.assertEqual(
                encrypted_fields,
                expected_encrypted_fields,
            )
