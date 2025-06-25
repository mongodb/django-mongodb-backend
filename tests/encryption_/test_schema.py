from django.db import connections

from .models import Patient
from .test_base import QueryableEncryptionTestCase


class SchemaTests(QueryableEncryptionTestCase):
    maxDiff = None

    def test_get_encrypted_fields_map(self):
        """
        Test class method called by schema editor and management command to get
        encrypted fields map for `create_collection` and `auto_encryption_opts`
        respectively. There are no data keys in the results.

        Data keys for the schema editor are created by
        `create_encrypted_collection` and data keys for the management command
        are created by the management command using code similar to the code in
        create_encrypted_collection` in Pymongo.
        """
        expected_encrypted_fields_map = {
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
            encrypted_fields_map = editor._get_encrypted_fields_map(Patient, client)
            for field in encrypted_fields_map["fields"]:
                # Remove data keys from the output; they are expected to differ
                field.pop("keyId", None)
            self.assertEqual(
                encrypted_fields_map,
                expected_encrypted_fields_map,
            )
