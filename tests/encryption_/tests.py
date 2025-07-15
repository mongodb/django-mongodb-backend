import json
from io import StringIO

from django.core.management import call_command
from django.db import connections
from django.test import TestCase, modify_settings, override_settings

from .models import Patient, PatientRecord
from .routers import TestEncryptedRouter

EXPECTED_ENCRYPTED_FIELDS_MAP = {
    "fields": [
        {
            "bsonType": "string",
            "path": "ssn",
            "queries": {"queryType": "equality", "contention": 1},
        },
        {"bsonType": "int", "path": "patient_id"},
        {"bsonType": "string", "path": "patient_name"},
    ]
}


@modify_settings(
    INSTALLED_APPS={"prepend": "django_mongodb_backend"},
)
@override_settings(DATABASE_ROUTERS=[TestEncryptedRouter()])
class EncryptedModelTests(TestCase):
    databases = {"default", "encrypted"}

    @classmethod
    def setUpTestData(cls):
        cls.patient_record = PatientRecord(ssn="123-45-6789")
        cls.patient = Patient(patient_id=1)
        cls.patient.save()

    def test_encrypted_fields_map(self):
        self.maxDiff = None
        with connections["encrypted"].schema_editor() as editor:
            self.assertCountEqual(
                {"fields": editor._get_encrypted_fields_map(self.patient)},
                EXPECTED_ENCRYPTED_FIELDS_MAP,
            )

    def test_auto_encryption_opts(self):
        out = StringIO()
        call_command("get_encrypted_fields_map", "--database", "encrypted", verbosity=0, stdout=out)
        self.assertIn(json.dumps(EXPECTED_ENCRYPTED_FIELDS_MAP, indent=2), out.getvalue())
