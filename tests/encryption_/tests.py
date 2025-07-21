import json
import sys
from datetime import datetime
from io import StringIO

import bson
import pymongo
from django.core.management import call_command
from django.db import connections
from django.test import TransactionTestCase, modify_settings, override_settings

from .models import Billing, Patient, PatientRecord
from .routers import TestEncryptedRouter

EXPECTED_ENCRYPTED_FIELDS_MAP = {
    "encrypted.billing": {
        "fields": [
            {"bsonType": "string", "path": "cc_type", "queries": {"queryType": "equality"}},
            {"bsonType": "long", "path": "cc_number", "queries": {"queryType": "equality"}},
            {"bsonType": "decimal", "path": "account_balance", "queries": {"queryType": "range"}},
        ]
    },
    "encrypted.patientrecord": {
        "fields": [
            {"bsonType": "string", "path": "ssn", "queries": {"queryType": "equality"}},
            {"bsonType": "date", "path": "birth_date", "queries": {"queryType": "range"}},
        ]
    },
    "encrypted.patient": {
        "fields": [
            {"bsonType": "int", "path": "patient_age", "queries": {"queryType": "range"}},
            {"bsonType": "int", "path": "patient_id"},
            {"bsonType": "string", "path": "patient_name"},
            {"bsonType": "string", "path": "patient_notes", "queries": {"queryType": "equality"}},
            {"bsonType": "date", "path": "registration_date", "queries": {"queryType": "equality"}},
            {"bsonType": "double", "path": "weight", "queries": {"queryType": "range"}},
        ]
    },
}


PATIENT_NOTES = """
This is a test patient record with sensitive information.
It includes personal details such as the patient's name, age, and medical history.
The patient's name is John Doe, aged 47. The record also contains notes about the patient's
condition and treatment.
"""


@modify_settings(
    INSTALLED_APPS={"prepend": "django_mongodb_backend"},
)
@override_settings(DATABASE_ROUTERS=[TestEncryptedRouter()])
class EncryptedModelTests(TransactionTestCase):
    databases = {"default", "encrypted"}
    available_apps = ["django_mongodb_backend", "encryption_"]

    @classmethod
    def setUp(self):
        self.billing = Billing(cc_type="Visa", cc_number=1234567890123456, account_balance=100.50)
        self.billing.save()

        self.patientrecord = PatientRecord(ssn="123-45-6789", birth_date="1970-01-01")
        self.patientrecord.save()

        self.patient = Patient(
            patient_id=1,
            patient_age=47,
            patient_name="John Doe",
            patient_notes=PATIENT_NOTES,
            registration_date=datetime(2023, 10, 1, 12, 0, 0),
            weight=175.5,
        )
        self.patient.save()

        # TODO: Embed billing and patient_record models in patient model then add tests

    def test_get_encrypted_fields_map_method(self):
        # Test the class method for getting encrypted fields map.
        self.maxDiff = None
        with connections["encrypted"].schema_editor() as editor:
            collection_name = self.patient._meta.db_table
            self.assertCountEqual(
                {"fields": editor._get_encrypted_fields_map(self.patient)},
                EXPECTED_ENCRYPTED_FIELDS_MAP[f"{'encrypted'}.{collection_name}"],
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

    def test_billing(self):
        # Test equality queries on encrypted fields.
        self.assertEqual(
            Billing.objects.get(cc_number=1234567890123456).cc_number, 1234567890123456
        )
        self.assertEqual(Billing.objects.get(cc_type="Visa").cc_type, "Visa")
        self.assertTrue(Billing.objects.filter(account_balance__gte=100.0).exists())

    def test_patientrecord(self):
        # Test range queries and equality queries on encrypted fields.
        self.assertEqual(PatientRecord.objects.get(ssn="123-45-6789").ssn, "123-45-6789")
        with self.assertRaises(PatientRecord.DoesNotExist):
            PatientRecord.objects.get(ssn="000-00-0000")
        self.assertTrue(PatientRecord.objects.filter(birth_date__gte="1969-01-01").exists())

    def test_patient(self):
        # Test range queries and equality queries on encrypted fields.
        self.assertTrue(Patient.objects.filter(patient_age__gte=40).exists())
        self.assertFalse(Patient.objects.filter(patient_age__gte=200).exists())
        self.assertEqual(
            Patient.objects.get(patient_notes=PATIENT_NOTES).patient_notes, PATIENT_NOTES
        )
        self.assertTrue(
            Patient.objects.get(
                registration_date=datetime(2023, 10, 1, 12, 0, 0)
            ).registration_date,
            datetime(2023, 10, 1, 12, 0, 0),
        )
        self.assertTrue(Patient.objects.filter(weight__gte=175.0).exists())

        # Test that the patient record exists in the encrypted database.
        patients = connections["encrypted"].database.patient.find()
        self.assertEqual(len(list(patients)), 1)

        # Test for decrypted patient record in the encrypted database.
        records = connections["encrypted"].database.patientrecord.find()
        self.assertTrue("__safeContent__" in records[0])

        # Test for encrypted patient record in unencrypted database.
        conn_params = connections["encrypted"].get_connection_params()
        if conn_params.pop("auto_encryption_opts", False):
            # Call MongoClient instead of get_new_connection because
            # get_new_connection will return the encrypted connection
            # from the connection pool.
            connection = pymongo.MongoClient(**conn_params)
            patientrecords = connection["test_encrypted"].patientrecord.find()
            ssn = patientrecords[0]["ssn"]
            self.assertTrue(isinstance(ssn, bson.binary.Binary))
            connection.close()
