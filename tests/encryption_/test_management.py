from io import StringIO

from bson import json_util
from django.core.management import call_command
from django.test import modify_settings

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
            field.pop("keyId", None)  # remove dynamic keyId
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
