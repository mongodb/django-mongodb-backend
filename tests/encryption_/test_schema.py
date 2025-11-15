from bson.binary import Binary
from django.core.exceptions import ImproperlyConfigured
from django.db import NotSupportedError, connections

from . import models
from .models import EncryptionKey
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
        "BinaryModel": {
            "fields": [
                {"bsonType": "binData", "path": "value", "queries": {"queryType": "equality"}}
            ]
        },
        "BooleanModel": {
            "fields": [{"bsonType": "bool", "path": "value", "queries": {"queryType": "equality"}}]
        },
        "CharModel": {
            "fields": [
                {"bsonType": "string", "path": "value", "queries": {"queryType": "equality"}}
            ]
        },
        "EmailModel": {
            "fields": [
                {"bsonType": "string", "path": "value", "queries": {"queryType": "equality"}}
            ]
        },
        "GenericIPAddressModel": {
            "fields": [
                {"bsonType": "string", "path": "value", "queries": {"queryType": "equality"}}
            ]
        },
        "TextModel": {
            "fields": [
                {"bsonType": "string", "path": "value", "queries": {"queryType": "equality"}}
            ]
        },
        "URLModel": {
            "fields": [
                {"bsonType": "string", "path": "value", "queries": {"queryType": "equality"}}
            ]
        },
        "BigIntegerModel": {
            "fields": [{"bsonType": "long", "path": "value", "queries": {"queryType": "range"}}]
        },
        "DateModel": {
            "fields": [{"bsonType": "date", "path": "value", "queries": {"queryType": "range"}}]
        },
        "DateTimeModel": {
            "fields": [{"bsonType": "date", "path": "value", "queries": {"queryType": "range"}}]
        },
        "DecimalModel": {
            "fields": [{"bsonType": "decimal", "path": "value", "queries": {"queryType": "range"}}]
        },
        "DurationModel": {
            "fields": [{"bsonType": "long", "path": "value", "queries": {"queryType": "range"}}]
        },
        "FloatModel": {
            "fields": [{"bsonType": "double", "path": "value", "queries": {"queryType": "range"}}]
        },
        "IntegerModel": {
            "fields": [{"bsonType": "long", "path": "value", "queries": {"queryType": "range"}}]
        },
        "PositiveBigIntegerModel": {
            "fields": [{"bsonType": "long", "path": "value", "queries": {"queryType": "range"}}]
        },
        "PositiveIntegerModel": {
            "fields": [{"bsonType": "long", "path": "value", "queries": {"queryType": "range"}}]
        },
        "PositiveSmallIntegerModel": {
            "fields": [{"bsonType": "int", "path": "value", "queries": {"queryType": "range"}}]
        },
        "SmallIntegerModel": {
            "fields": [{"bsonType": "int", "path": "value", "queries": {"queryType": "range"}}]
        },
        "TimeModel": {
            "fields": [{"bsonType": "date", "path": "value", "queries": {"queryType": "range"}}]
        },
    }

    def test_get_encrypted_fields_all_models(self):
        """
        Loops through all models,
        checks their encrypted fields map from the schema editor,
        and compares to expected BSON type & queries mapping.
        """
        # Deleting all keys is only correct only if this test includes all
        # test models. This test may not be needed since it's tested when the
        # test runner migrates all models. If any subTest fails, the key vault
        # will be left in an inconsistent state.
        EncryptionKey.objects.all().delete()
        connection = connections["encrypted"]
        for model_name, expected in self.expected_map.items():
            with self.subTest(model=model_name):
                model_class = getattr(models, model_name)
                with connection.schema_editor() as editor:
                    encrypted_fields = editor._get_encrypted_fields(model_class)
                    for field in encrypted_fields["fields"]:
                        del field["keyId"]  # Can't compare dynamic value
                    self.assertEqual(encrypted_fields, expected)

    def test_key_creation_and_lookup(self):
        """
        Use _get_encrypted_fields to
        generate and store a data key in the vault, then
        query the vault with the keyAltName.
        """
        model_class = models.CharModel
        test_key_alt_name = f"{model_class._meta.db_table}.value"
        # Delete the test key and verify it's gone.
        EncryptionKey.objects.filter(key_alt_name=test_key_alt_name).delete()
        with self.assertRaises(EncryptionKey.DoesNotExist):
            EncryptionKey.objects.get(key_alt_name=test_key_alt_name)
        # Regenerate the keyId.
        with connections["encrypted"].schema_editor() as editor:
            encrypted_fields = editor._get_encrypted_fields(model_class)
        # Validate schema contains a keyId for the field.
        field_info = encrypted_fields["fields"][0]
        self.assertEqual(field_info["path"], "value")
        self.assertIsInstance(field_info["keyId"], Binary)
        # Lookup in key vault by the keyAltName.
        key = EncryptionKey.objects.get(key_alt_name=test_key_alt_name)
        self.assertEqual(key.id, field_info["keyId"])
        self.assertEqual(key.key_alt_name, [test_key_alt_name])

    def test_missing_auto_encryption_opts(self):
        connection = connections["default"]
        msg = (
            "Tried to create model encryption_.Patient in 'default' database. "
            "The model has encrypted fields but DATABASES['default']['OPTIONS'] "
            'is missing the "auto_encryption_opts" parameter. If the model '
            "should not be created in this database, adjust your database "
            "routers."
        )
        with (
            self.assertRaisesMessage(ImproperlyConfigured, msg),
            connection.schema_editor() as editor,
        ):
            editor.create_model(models.Patient)

    def test_multiple_kms_providers(self):
        connection = connections["encrypted"]
        auto_encryption_opts = connection.connection._options.auto_encryption_opts
        kms_providers = auto_encryption_opts._kms_providers
        # Mock multiple kms_providers by using a list of length > 1.
        auto_encryption_opts._kms_providers = [{}, {}]
        msg = (
            "Multiple KMS providers per database aren't supported. Please "
            "create a feature request with details about your use case."
        )
        try:
            with (
                self.assertRaisesMessage(NotSupportedError, msg),
                connection.schema_editor() as editor,
            ):
                editor.create_model(models.Patient)
        finally:
            # Restore the original value.
            auto_encryption_opts._kms_providers = kms_providers
