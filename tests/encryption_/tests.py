import json
import sys
from io import StringIO

from django.core.management import call_command
from django.db import connections
from django.test import TestCase, modify_settings, override_settings

from .models import Patient, PatientRecord
from .routers import TestEncryptedRouter

EXPECTED_ENCRYPTED_FIELDS_MAP = {
    "encrypted.billing": {
        "fields": [
            {"bsonType": "string", "path": "cc_type", "queries": {"queryType": "equality"}},
            {"bsonType": "int", "path": "cc_number", "queries": {"queryType": "equality"}},
        ]
    },
    "encrypted.patientrecord": {
        "fields": [{"bsonType": "string", "path": "ssn", "queries": {"queryType": "equality"}}]
    },
    "encrypted.patient": {
        "fields": [
            {"bsonType": "int", "path": "patient_age", "queries": {"queryType": "range"}},
            {"bsonType": "int", "path": "patient_id"},
            {"bsonType": "string", "path": "patient_name"},
        ]
    },
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
        cls.patient_record.save()
        cls.patient = Patient(patient_id=1, patient_age=47)
        cls.patient.save()

    def test_get_encrypted_fields_map_method(self):
        self.maxDiff = None
        db_name = "encrypted"
        with connections[db_name].schema_editor() as editor:
            collection_name = self.patient._meta.db_table
            self.assertCountEqual(
                {"fields": editor._get_encrypted_fields_map(self.patient)},
                EXPECTED_ENCRYPTED_FIELDS_MAP[f"{db_name}.{collection_name}"],
            )

    def test_get_encrypted_fields_map_command(self):
        class Tee(StringIO):
            """Print the output of management commands to stdout."""

            def write(self, txt):
                sys.stdout.write(txt)
                super().write(txt)

        out = Tee()
        call_command("get_encrypted_fields_map", "--database", "encrypted", verbosity=0, stdout=out)
        self.assertIn(json.dumps(EXPECTED_ENCRYPTED_FIELDS_MAP, indent=2), out.getvalue())

    def test_equality_query(self):
        self.assertEqual(PatientRecord.objects.get(ssn="123-45-6789").ssn, "123-45-6789")
        with self.assertRaises(PatientRecord.DoesNotExist):
            PatientRecord.objects.get(ssn="000-00-0000")

    def test_range_query(self):
        self.assertTrue(Patient.objects.filter(patient_age__gte=40).exists())
        self.assertFalse(Patient.objects.filter(patient_age__gte=200).exists())
