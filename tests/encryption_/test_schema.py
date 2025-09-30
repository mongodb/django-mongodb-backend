from bson.binary import Binary
from django.db import connections

from . import models
from .test_base import EncryptionTestCase


class SchemaTests(EncryptionTestCase):
    # Expected encrypted fields map per model
    expected_map = {
        "Patient": {
            "fields": [
                {
                    "bsonType": "string",
                    "path": "patient_record.ssn",
                    "queries": {"queryType": "equality"},
                },
                {"bsonType": "object", "path": "patient_record.billing"},
            ]
        },
        "EncryptedBinaryTest": {
            "fields": [
                {"bsonType": "binData", "path": "value", "queries": {"queryType": "equality"}}
            ]
        },
        "EncryptedBooleanTest": {
            "fields": [{"bsonType": "bool", "path": "value", "queries": {"queryType": "equality"}}]
        },
        "EncryptedCharTest": {
            "fields": [
                {"bsonType": "string", "path": "value", "queries": {"queryType": "equality"}}
            ]
        },
        "EncryptedEmailTest": {
            "fields": [
                {"bsonType": "string", "path": "value", "queries": {"queryType": "equality"}}
            ]
        },
        "EncryptedGenericIPAddressTest": {
            "fields": [
                {"bsonType": "string", "path": "value", "queries": {"queryType": "equality"}}
            ]
        },
        "EncryptedTextTest": {
            "fields": [
                {"bsonType": "string", "path": "value", "queries": {"queryType": "equality"}}
            ]
        },
        "EncryptedURLTest": {
            "fields": [
                {"bsonType": "string", "path": "value", "queries": {"queryType": "equality"}}
            ]
        },
        "EncryptedBigIntegerTest": {
            "fields": [{"bsonType": "long", "path": "value", "queries": {"queryType": "range"}}]
        },
        "EncryptedDateTest": {
            "fields": [{"bsonType": "date", "path": "value", "queries": {"queryType": "range"}}]
        },
        "EncryptedDateTimeTest": {
            "fields": [{"bsonType": "date", "path": "value", "queries": {"queryType": "range"}}]
        },
        "EncryptedDecimalTest": {
            "fields": [{"bsonType": "decimal", "path": "value", "queries": {"queryType": "range"}}]
        },
        "EncryptedDurationTest": {
            "fields": [{"bsonType": "long", "path": "value", "queries": {"queryType": "range"}}]
        },
        "EncryptedFloatTest": {
            "fields": [{"bsonType": "double", "path": "value", "queries": {"queryType": "range"}}]
        },
        "EncryptedIntegerTest": {
            "fields": [{"bsonType": "long", "path": "value", "queries": {"queryType": "range"}}]
        },
        "EncryptedPositiveBigIntegerTest": {
            "fields": [{"bsonType": "long", "path": "value", "queries": {"queryType": "range"}}]
        },
        "EncryptedPositiveIntegerTest": {
            "fields": [{"bsonType": "long", "path": "value", "queries": {"queryType": "range"}}]
        },
        "EncryptedPositiveSmallIntegerTest": {
            "fields": [{"bsonType": "int", "path": "value", "queries": {"queryType": "range"}}]
        },
        "EncryptedSmallIntegerTest": {
            "fields": [{"bsonType": "int", "path": "value", "queries": {"queryType": "range"}}]
        },
        "EncryptedTimeTest": {
            "fields": [{"bsonType": "date", "path": "value", "queries": {"queryType": "range"}}]
        },
    }

    def test_get_encrypted_fields_all_models(self):
        """
        Loops through all Encrypted*Test models,
        checks their encrypted fields map from the schema editor,
        and compares to expected BSON type & queries mapping.
        """
        connection = connections["encrypted"]

        for model_name, expected in self.expected_map.items():
            with self.subTest(model=model_name):
                model_class = getattr(models, model_name)
                with connection.schema_editor() as editor:
                    client = connection.connection
                    encrypted_fields = editor._get_encrypted_fields(model_class, client)
                    for field in encrypted_fields["fields"]:
                        field.pop("keyId", None)  # Remove dynamic value
                    self.assertEqual(encrypted_fields, expected)

    def test_key_creation_and_lookup(self):
        """
        Use _get_encrypted_fields(create_data_keys=True) to
        generate and store a data key in the vault, then
        query the vault with the keyAltName.
        """
        connection = connections["encrypted"]
        client = connection.connection
        auto_encryption_opts = client._options.auto_encryption_opts

        key_vault_db, key_vault_coll = auto_encryption_opts._key_vault_namespace.split(".", 1)
        vault_coll = client[key_vault_db][key_vault_coll]

        model_class = models.EncryptedCharTest
        test_key_alt_name = f"{model_class._meta.db_table}.value"
        vault_coll.delete_many({"keyAltNames": test_key_alt_name})

        # Call _get_encrypted_fields with create_data_keys=True
        with connection.schema_editor() as editor:
            encrypted_fields = editor._get_encrypted_fields(model_class, create_data_keys=True)

        # Validate schema contains a keyId for our field
        self.assertTrue(encrypted_fields["fields"])
        field_info = encrypted_fields["fields"][0]
        self.assertEqual(field_info["path"], "value")
        self.assertIsInstance(field_info["keyId"], Binary)

        # Lookup in key vault by the keyAltName created
        key_doc = vault_coll.find_one({"keyAltNames": test_key_alt_name})
        self.assertIsNotNone(key_doc, "Key should exist in vault")
        self.assertEqual(key_doc["_id"], field_info["keyId"])
        self.assertIn(test_key_alt_name, key_doc["keyAltNames"])
