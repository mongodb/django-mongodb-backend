from io import StringIO

from bson import json_util
from django.core.management import call_command
from django.test import modify_settings, override_settings

from .routers import TestEncryptedRouter
from .test_base import QueryableEncryptionTestCase


@modify_settings(
    INSTALLED_APPS={"prepend": "django_mongodb_backend"},
)
@override_settings(DATABASE_ROUTERS=[TestEncryptedRouter()])
class QueryableEncryptionCommandTests(QueryableEncryptionTestCase):
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
                "path": "profile_picture",
                "queries": {"queryType": "equality"},
            },
            {
                "bsonType": "int",
                "path": "patient_age",
                "queries": {"queryType": "range", "max": 100, "min": 0},
            },
            {
                "bsonType": "double",
                "path": "weight",
                "queries": {"queryType": "range"},
            },
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
            "--create-new-keys",
            verbosity=0,
            stdout=out,
        )
        command_output = json_util.loads(out.getvalue())
        self._compare_output(
            self.expected_patient_record,
            command_output["encryption__patientrecord"],
        )
