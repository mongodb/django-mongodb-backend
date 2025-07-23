import importlib
import json
import os
import sys
from datetime import datetime
from io import StringIO
from unittest.mock import patch

import bson
import pymongo
from django.core.management import call_command
from django.db import connections
from django.test import TestCase, TransactionTestCase, modify_settings, override_settings
from pymongo_auth_aws.auth import AwsCredential

from .models import Billing, Patient, PatientRecord
from .routers import TestEncryptedRouter

EXPECTED_ENCRYPTED_FIELDS_MAP = {
    "test_encrypted.billing": {
        "fields": [
            {"bsonType": "string", "path": "cc_type", "queries": {"queryType": "equality"}},
            {"bsonType": "long", "path": "cc_number", "queries": {"queryType": "equality"}},
            {"bsonType": "decimal", "path": "account_balance", "queries": {"queryType": "range"}},
        ]
    },
    "test_encrypted.patientrecord": {
        "fields": [
            {"bsonType": "string", "path": "ssn", "queries": {"queryType": "equality"}},
            {"bsonType": "date", "path": "birth_date", "queries": {"queryType": "range"}},
            {
                "bsonType": "binData",
                "path": "profile_picture",
                "queries": {"queryType": "equality"},
            },
            {"bsonType": "int", "path": "patient_age", "queries": {"queryType": "range"}},
            {"bsonType": "double", "path": "weight", "queries": {"queryType": "range"}},
        ]
    },
    "test_encrypted.patient": {
        "fields": [
            {"bsonType": "int", "path": "patient_id", "queries": {"queryType": "equality"}},
            {"bsonType": "string", "path": "patient_name"},
            {"bsonType": "string", "path": "patient_notes", "queries": {"queryType": "equality"}},
            {"bsonType": "date", "path": "registration_date", "queries": {"queryType": "equality"}},
            {"bsonType": "bool", "path": "is_active", "queries": {"queryType": "equality"}},
        ]
    },
}


def reload_module(module):
    """
    Reloads a module to ensure that any changes to environment variables
    or other settings are applied without restarting the test runner.
    """
    module = importlib.import_module(module)
    importlib.reload(module)
    return module


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

        self.patientrecord = PatientRecord(
            ssn="123-45-6789",
            birth_date="1970-01-01",
            profile_picture=b"image data",
            weight=175.5,
            patient_age=47,
        )
        self.patientrecord.save()

        self.patient = Patient(
            patient_id=1,
            patient_name="John Doe",
            patient_notes="patient notes " * 25,
            registration_date=datetime(2023, 10, 1, 12, 0, 0),
            is_active=True,
        )
        self.patient.save()

        # TODO: Embed billing and patient_record models in patient model then add tests

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.patch_aws = patch(
            "pymongocrypt.synchronous.credentials.aws_temp_credentials",
            return_value=AwsCredential(username="", password="", token=""),
        )
        cls.patch_aws.start()

        cls.patch_azure = patch(
            "pymongocrypt.synchronous.credentials._get_azure_credentials", return_value={}
        )
        cls.patch_azure.start()

        cls.patch_gcp = patch(
            "pymongocrypt.synchronous.credentials._get_gcp_credentials", return_value={}
        )
        cls.patch_gcp.start()

    @classmethod
    def tearDownClass(cls):
        cls.patch_aws.stop()
        cls.patch_azure.stop()
        cls.patch_gcp.stop()

    def test_get_encrypted_fields_map_method(self):
        self.maxDiff = None
        with connections["encrypted"].schema_editor() as editor:
            collection_name = self.patient._meta.db_table
            self.assertCountEqual(
                {"fields": editor._get_encrypted_fields_map(self.patient)},
                EXPECTED_ENCRYPTED_FIELDS_MAP[f"{'test_encrypted'}.{collection_name}"],
            )

    def test_get_encrypted_fields_map_command(self):
        # TODO: Remove before merge
        class Tee(StringIO):
            def write(self, txt):
                sys.stdout.write(txt)
                super().write(txt)

        out = Tee()

        # out = StringIO()
        call_command("get_encrypted_fields_map", "--database", "encrypted", verbosity=0, stdout=out)
        self.assertIn(json.dumps(EXPECTED_ENCRYPTED_FIELDS_MAP, indent=2), out.getvalue())

    def test_billing(self):
        self.assertEqual(
            Billing.objects.get(cc_number=1234567890123456).cc_number, 1234567890123456
        )
        self.assertEqual(Billing.objects.get(cc_type="Visa").cc_type, "Visa")
        self.assertTrue(Billing.objects.filter(account_balance__gte=100.0).exists())

    def test_patientrecord(self):
        self.assertEqual(PatientRecord.objects.get(ssn="123-45-6789").ssn, "123-45-6789")
        with self.assertRaises(PatientRecord.DoesNotExist):
            PatientRecord.objects.get(ssn="000-00-0000")
        self.assertTrue(PatientRecord.objects.filter(birth_date__gte="1969-01-01").exists())
        self.assertEqual(
            PatientRecord.objects.get(ssn="123-45-6789").profile_picture, b"image data"
        )
        with self.assertRaises(AssertionError):
            self.assertEqual(
                PatientRecord.objects.get(ssn="123-45-6789").profile_picture, b"bad image data"
            )
        self.assertTrue(PatientRecord.objects.filter(patient_age__gte=40).exists())
        self.assertFalse(PatientRecord.objects.filter(patient_age__gte=200).exists())
        self.assertTrue(PatientRecord.objects.filter(weight__gte=175.0).exists())

    def test_patient(self):
        self.assertEqual(
            Patient.objects.get(patient_notes="patient notes " * 25).patient_notes,
            "patient notes " * 25,
        )
        self.assertTrue(
            Patient.objects.get(
                registration_date=datetime(2023, 10, 1, 12, 0, 0)
            ).registration_date,
            datetime(2023, 10, 1, 12, 0, 0),
        )
        self.assertTrue(Patient.objects.get(patient_id=1).is_active)

        # Test decrypted patient record in encrypted database.
        patients = connections["encrypted"].database.patient.find()
        self.assertEqual(len(list(patients)), 1)
        records = connections["encrypted"].database.patientrecord.find()
        self.assertTrue("__safeContent__" in records[0])

        # Test encrypted patient record in unencrypted database.
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


class KMSCredentialsTests(TestCase):
    def test_env(self):
        with patch.dict(os.environ, {}, clear=True):
            encryption = reload_module("django_mongodb_backend.encryption")
            self.assertEqual(encryption.KMS_CREDENTIALS["aws"]["key"], "")
            self.assertEqual(encryption.KMS_CREDENTIALS["aws"]["region"], "")
            self.assertEqual(encryption.KMS_CREDENTIALS["azure"]["keyName"], "")
            self.assertEqual(encryption.KMS_CREDENTIALS["azure"]["keyVaultEndpoint"], "")
            self.assertEqual(encryption.KMS_CREDENTIALS["gcp"]["projectId"], "")
            self.assertEqual(encryption.KMS_CREDENTIALS["gcp"]["location"], "")
            self.assertEqual(encryption.KMS_CREDENTIALS["gcp"]["keyRing"], "")
            self.assertEqual(encryption.KMS_CREDENTIALS["gcp"]["keyName"], "")
        env = {
            "AWS_KEY_ARN": "TestArn",
            "AWS_KEY_REGION": "us-x-test",
            "AZURE_KEY_NAME": "azure-key",
            "AZURE_KEY_VAULT_ENDPOINT": "https://example.vault.azure.net/",
            "GCP_PROJECT_ID": "gcp-test-prj",
            "GCP_LOCATION": "test-loc",
            "GCP_KEY_RING": "ring1",
            "GCP_KEY_NAME": "gcp-key",
        }
        with patch.dict(os.environ, env, clear=True):
            encryption = reload_module("django_mongodb_backend.encryption")
            self.assertEqual(encryption.KMS_CREDENTIALS["azure"]["keyName"], "azure-key")
            self.assertEqual(
                encryption.KMS_CREDENTIALS["azure"]["keyVaultEndpoint"],
                "https://example.vault.azure.net/",
            )
            self.assertEqual(encryption.KMS_CREDENTIALS["gcp"]["projectId"], "gcp-test-prj")
            self.assertEqual(encryption.KMS_CREDENTIALS["gcp"]["location"], "test-loc")
            self.assertEqual(encryption.KMS_CREDENTIALS["gcp"]["keyRing"], "ring1")
            self.assertEqual(encryption.KMS_CREDENTIALS["gcp"]["keyName"], "gcp-key")


class KMSProvidersTests(TestCase):
    def test_env(self):
        with patch.dict(os.environ, {}, clear=True):
            encryption = reload_module("django_mongodb_backend.encryption")
            self.assertEqual(encryption.KMS_PROVIDERS["kmip"]["endpoint"], "not a valid endpoint")
        env = {
            "KMIP_KMS_ENDPOINT": "kmip://loc",
        }
        with patch.dict(os.environ, env, clear=True):
            encryption = reload_module("django_mongodb_backend.encryption")
            self.assertEqual(encryption.KMS_PROVIDERS["kmip"]["endpoint"], "kmip://loc")
