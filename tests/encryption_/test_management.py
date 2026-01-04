from io import StringIO

from bson import json_util
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.db import connections
from django.test import modify_settings

from .models import EncryptionKey
from .test_base import EncryptionTestCase


@modify_settings(INSTALLED_APPS={"prepend": "django_mongodb_backend"})
class CommandTests(EncryptionTestCase):
    # Expected encrypted field maps for all Encrypted* models
    expected_maps = {
        "encryption__patient": {
            "fields": [
                {
                    "bsonType": "string",
                    "path": "patient_record.ssn",
                    "queries": {"queryType": "equality"},
                },
                {"bsonType": "object", "path": "patient_record.billing"},
            ]
        },
        # Equality-queryable fields
        "encryption__binarymodel": {
            "fields": [
                {"bsonType": "binData", "path": "value", "queries": {"queryType": "equality"}}
            ]
        },
        "encryption__booleanmodel": {
            "fields": [{"bsonType": "bool", "path": "value", "queries": {"queryType": "equality"}}]
        },
        "encryption__charmodel": {
            "fields": [
                {"bsonType": "string", "path": "value", "queries": {"queryType": "equality"}}
            ]
        },
        "encryption__emailmodel": {
            "fields": [
                {"bsonType": "string", "path": "value", "queries": {"queryType": "equality"}}
            ]
        },
        "encryption__genericipaddressmodel": {
            "fields": [
                {"bsonType": "string", "path": "value", "queries": {"queryType": "equality"}}
            ]
        },
        "encryption__textmodel": {
            "fields": [
                {"bsonType": "string", "path": "value", "queries": {"queryType": "equality"}}
            ]
        },
        "encryption__urlmodel": {
            "fields": [
                {"bsonType": "string", "path": "value", "queries": {"queryType": "equality"}}
            ]
        },
        # Range-queryable fields
        "encryption__bigintegermodel": {
            "fields": [{"bsonType": "long", "path": "value", "queries": {"queryType": "range"}}]
        },
        "encryption__datemodel": {
            "fields": [{"bsonType": "date", "path": "value", "queries": {"queryType": "range"}}]
        },
        "encryption__datetimemodel": {
            "fields": [{"bsonType": "date", "path": "value", "queries": {"queryType": "range"}}]
        },
        "encryption__decimalmodel": {
            "fields": [{"bsonType": "decimal", "path": "value", "queries": {"queryType": "range"}}]
        },
        "encryption__durationmodel": {
            "fields": [{"bsonType": "long", "path": "value", "queries": {"queryType": "range"}}]
        },
        "encryption__floatmodel": {
            "fields": [{"bsonType": "double", "path": "value", "queries": {"queryType": "range"}}]
        },
        "encryption__integermodel": {
            "fields": [{"bsonType": "long", "path": "value", "queries": {"queryType": "range"}}]
        },
        "encryption__positivebigintegermodel": {
            "fields": [{"bsonType": "long", "path": "value", "queries": {"queryType": "range"}}]
        },
        "encryption__positiveintegermodel": {
            "fields": [{"bsonType": "long", "path": "value", "queries": {"queryType": "range"}}]
        },
        "encryption__positivesmallintegermodel": {
            "fields": [{"bsonType": "int", "path": "value", "queries": {"queryType": "range"}}]
        },
        "encryption__smallintegermodel": {
            "fields": [{"bsonType": "int", "path": "value", "queries": {"queryType": "range"}}]
        },
        "encryption__timemodel": {
            "fields": [{"bsonType": "date", "path": "value", "queries": {"queryType": "range"}}]
        },
    }

    def _compare_output(self, expected, actual):
        for field in actual["fields"]:
            del field["keyId"]  # Can't compare dynamic value
        self.assertEqual(expected, actual)

    def test_show_encrypted_fields_map(self):
        out = StringIO()
        call_command("showencryptedfieldsmap", "--database", "encrypted", verbosity=0, stdout=out)
        command_output = json_util.loads(out.getvalue())

        # Loop through each expected model
        for model_key, expected in self.expected_maps.items():
            with self.subTest(model=model_key):
                self.assertIn(model_key, command_output)
                self._compare_output(expected, command_output[model_key])

    def test_missing_key(self):
        connection = connections["encrypted"]
        auto_encryption_opts = connection.connection._options.auto_encryption_opts
        kms_providers = auto_encryption_opts._kms_providers
        test_key = "encryption__patient.patient_record.ssn"
        msg = (
            f"Encryption key {test_key} not found. Have migrated the "
            "<class 'encryption_.models.PatientRecord'> model?"
        )
        EncryptionKey.objects.filter(key_alt_name=test_key).delete()
        try:
            with self.assertRaisesMessage(ImproperlyConfigured, msg):
                call_command("showencryptedfieldsmap", "--database", "encrypted", verbosity=0)
        finally:
            # Replace the deleted key.
            kms_provider = next(iter(kms_providers.keys()))
            credentials = connection.settings_dict.get("KMS_CREDENTIALS")
            master_key = credentials[kms_provider] if credentials else None
            connection.client_encryption.create_data_key(
                kms_provider=kms_provider,
                master_key=master_key,
                key_alt_names=[test_key],
            )
