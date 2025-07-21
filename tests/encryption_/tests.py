import json
import sys
from io import StringIO

import bson
import pymongo
from django.core.management import call_command
from django.db import connections
from django.test import TransactionTestCase, modify_settings, override_settings

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
class EncryptedModelTests(TransactionTestCase):
    databases = {"default", "encrypted"}
    available_apps = ["django_mongodb_backend", "encryption_"]

    @classmethod
    def setUp(self):
        self.patient_record = PatientRecord(ssn="123-45-6789")
        self.patient_record.save()

        self.patient = Patient(patient_id=1, patient_age=47, patient_name="John Doe")
        self.patient.save()

        # TODO: Embed billing and patient_record in patient then test

    def test_get_encrypted_fields_map_method(self):
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

    def test_patientrecord(self):
        self.assertTrue(Patient.objects.filter(patient_age__gte=40).exists())
        self.assertFalse(Patient.objects.filter(patient_age__gte=200).exists())

    def test_patient(self):
        self.assertEqual(PatientRecord.objects.get(ssn="123-45-6789").ssn, "123-45-6789")
        with self.assertRaises(PatientRecord.DoesNotExist):
            PatientRecord.objects.get(ssn="000-00-0000")

    def test_patient_record_exists(self):
        patients = connections["encrypted"].database.patient.find()
        self.assertEqual(len(list(patients)), 1)

        # Check for decrypted content
        records = connections["encrypted"].database.patientrecord.find()
        self.assertTrue("__safeContent__" in records[0])

    def test_patient_record_exists_and_is_encrypted(self):
        # Check that the patient record is encrypted from an unencrypted connection.
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
