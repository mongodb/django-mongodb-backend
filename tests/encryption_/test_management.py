from io import StringIO

from bson import json_util
from django.core.management import call_command
from django.test import TransactionTestCase, modify_settings, override_settings, skipUnlessDBFeature

from .routers import TestEncryptedRouter


@skipUnlessDBFeature("supports_queryable_encryption")
@modify_settings(
    INSTALLED_APPS={"prepend": "django_mongodb_backend"},
)
@override_settings(DATABASE_ROUTERS=[TestEncryptedRouter()])
class CommandTests(TransactionTestCase):
    available_apps = ["django_mongodb_backend", "encryption_"]
    maxDiff = None
    expected_patient_record = {
        "fields": [
            {
                "bsonType": "string",
                "path": "ssn",
                "queries": {"queryType": "equality"},
            },
            {
                "bsonType": "date",
                "path": "birth_date",
                "queries": {"queryType": "range"},
            },
            {
                "bsonType": "binData",
                "path": "profile_picture_data",
                "queries": {"queryType": "equality"},
            },
            {
                "bsonType": "int",
                "path": "age",
                "queries": {"queryType": "range", "max": 100, "min": 0},
            },
            {
                "bsonType": "double",
                "path": "weight",
                "queries": {"queryType": "range"},
            },
            {
                "bsonType": "long",
                "path": "insurance_policy_number",
                "queries": {"queryType": "equality"},
            },
            {
                "bsonType": "long",
                "path": "emergency_contacts_count",
                "queries": {"queryType": "equality"},
            },
            {"bsonType": "int", "path": "completed_visits", "queries": {"queryType": "equality"}},
        ]
    }

    def _compare_output(self, json1, json2):
        # Remove keyIds since they are different for each run.
        for field in json2["fields"]:
            del field["keyId"]
        self.assertEqual(json1, json2)

    def test_show_encrypted_fields_map(self):
        out = StringIO()
        call_command(
            "showencryptedfieldsmap",
            "--database",
            "encrypted",
            verbosity=0,
            stdout=out,
        )
        command_output = json_util.loads(out.getvalue())
        self._compare_output(
            self.expected_patient_record,
            command_output["encryption__patientrecord"],
        )

    def test_create_new_keys(self):
        out = StringIO()
        call_command(
            "showencryptedfieldsmap",
            "--database",
            "encrypted",
            "--create-data-keys",
            verbosity=0,
            stdout=out,
        )
        command_output = json_util.loads(out.getvalue())
        self._compare_output(
            self.expected_patient_record,
            command_output["encryption__patientrecord"],
        )
