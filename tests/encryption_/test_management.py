from io import StringIO

from bson import json_util
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.test import modify_settings

from .models import KeyTestModel
from .test_base import EncryptionTestCase


@modify_settings(INSTALLED_APPS={"prepend": "django_mongodb_backend"})
class ShowEncryptedFieldsTests(EncryptionTestCase):
    # Expected encrypted field maps for all models with encrypted fields.
    expected_maps = {
        "encryption__arraymodel": {"fields": [{"bsonType": "array", "path": "values"}]},
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
        "encryption__movie": {"fields": [{"bsonType": "array", "path": "cast"}]},
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
        "encryption__objectidmodel": {
            "fields": [
                {"bsonType": "objectId", "path": "value", "queries": {"queryType": "equality"}}
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
        "encryption__uuidmodel": {
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

    def test_ouput(self):
        """The expected output appears for each model."""
        out = StringIO()
        call_command("showencryptedfieldsmap", "--database", "encrypted", verbosity=0, stdout=out)
        parsed_output = json_util.loads(out.getvalue())
        # All models accounted for and no extra models.
        self.assertEqual(len(parsed_output), len(self.expected_maps))
        for model_key, expected in self.expected_maps.items():
            with self.subTest(model=model_key):
                self.assertIn(model_key, parsed_output)
                model_data = parsed_output[model_key]
                for field in model_data["fields"]:
                    del field["keyId"]  # Can't compare dynamic value
                self.assertEqual(expected, model_data)

    def test_missing_key(self):
        """
        ImproperlyConfigured is raised when an encryption key isn't found for a
        model.
        """
        msg = (
            "Encryption key 'encryption__keytestmodel.value' not found. Have "
            "you migrated the encryption_.KeyTestModel model?"
        )
        # showencryptedfieldsmap ignores unmanaged models, so fake that this
        # model is managed.
        KeyTestModel._meta.managed = True
        try:
            with self.assertRaisesMessage(ImproperlyConfigured, msg):
                call_command("showencryptedfieldsmap", "--database", "encrypted", verbosity=0)
        finally:
            # Restore original state.
            KeyTestModel._meta.managed = False
