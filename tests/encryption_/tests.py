import base64
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

from .models import Billing, Patient, PatientRecord
from .routers import TestEncryptedRouter

ENCRYPTION_MODULE_PATH = "django_mongodb_backend.encryption"

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
            {
                "bsonType": "binData",
                "path": "profile_picture",
                "queries": {"queryType": "equality"},
            },
            {"bsonType": "int", "path": "patient_age", "queries": {"queryType": "range"}},
            {"bsonType": "double", "path": "weight", "queries": {"queryType": "range"}},
        ]
    },
    "encrypted.patient": {
        "fields": [
            {"bsonType": "int", "path": "patient_id", "queries": {"queryType": "equality"}},
            {"bsonType": "string", "path": "patient_name"},
            {"bsonType": "string", "path": "patient_notes", "queries": {"queryType": "equality"}},
            {"bsonType": "date", "path": "registration_date", "queries": {"queryType": "equality"}},
            {"bsonType": "bool", "path": "is_active", "queries": {"queryType": "equality"}},
        ]
    },
}


PATIENT_NOTES = """
This is a test patient record with sensitive information.
It includes personal details such as the patient's name, age, and medical history.
The patient's name is John Doe, aged 47. The record also contains notes about the patient's
condition and treatment.
"""


PROFILE_PICTURE = b"test_image_data"  # Simulated binary data for the profile picture


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
            profile_picture=PROFILE_PICTURE,
            weight=175.5,
            patient_age=47,
        )
        self.patientrecord.save()

        self.patient = Patient(
            patient_id=1,
            patient_name="John Doe",
            patient_notes=PATIENT_NOTES,
            registration_date=datetime(2023, 10, 1, 12, 0, 0),
            is_active=True,
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
        self.assertEqual(
            PatientRecord.objects.get(ssn="123-45-6789").profile_picture, PROFILE_PICTURE
        )
        with self.assertRaises(AssertionError):
            self.assertEqual(
                PatientRecord.objects.get(ssn="123-45-6789").profile_picture, b"some_binary_data"
            )
        self.assertTrue(PatientRecord.objects.filter(patient_age__gte=40).exists())
        self.assertFalse(PatientRecord.objects.filter(patient_age__gte=200).exists())
        self.assertTrue(PatientRecord.objects.filter(weight__gte=175.0).exists())

    def test_patient(self):
        # Test range queries and equality queries on encrypted fields.
        self.assertEqual(
            Patient.objects.get(patient_notes=PATIENT_NOTES).patient_notes, PATIENT_NOTES
        )
        self.assertTrue(
            Patient.objects.get(
                registration_date=datetime(2023, 10, 1, 12, 0, 0)
            ).registration_date,
            datetime(2023, 10, 1, 12, 0, 0),
        )
        self.assertTrue(Patient.objects.get(patient_id=1).is_active)

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


class KMSConfigTests(TestCase):
    # TODO: Consider integration with on-demand KMS configuration
    # provided by libmongocrypt.
    # https://pymongo.readthedocs.io/en/stable/examples/encryption.html#csfle-on-demand-credentials

    def reload_encryption_module(self):
        # Reload encryption module so environment variable changes take effect
        encryption_module = importlib.import_module(ENCRYPTION_MODULE_PATH)
        importlib.reload(encryption_module)
        return encryption_module

    def test_kms_credentials_default(self):
        with patch.dict(os.environ, {}, clear=True):
            kms_mod = self.reload_encryption_module()
            KMS_CREDENTIALS = kms_mod.KMS_CREDENTIALS

            self.assertEqual(KMS_CREDENTIALS["aws"]["key"], "")
            self.assertEqual(KMS_CREDENTIALS["aws"]["region"], "")
            self.assertEqual(KMS_CREDENTIALS["azure"]["keyName"], "")
            self.assertEqual(KMS_CREDENTIALS["azure"]["keyVaultEndpoint"], "")
            self.assertEqual(KMS_CREDENTIALS["gcp"]["projectId"], "")
            self.assertEqual(KMS_CREDENTIALS["gcp"]["location"], "")
            self.assertEqual(KMS_CREDENTIALS["gcp"]["keyRing"], "")
            self.assertEqual(KMS_CREDENTIALS["gcp"]["keyName"], "")
            self.assertEqual(KMS_CREDENTIALS["kmip"], {})
            self.assertEqual(KMS_CREDENTIALS["local"], {})

    def test_kms_providers_default(self):
        with patch.dict(os.environ, {}, clear=True):
            kms_mod = self.reload_encryption_module()
            KMS_PROVIDERS = kms_mod.KMS_PROVIDERS

            self.assertEqual(KMS_PROVIDERS["aws"]["accessKeyId"], "not an access key")
            self.assertEqual(KMS_PROVIDERS["aws"]["secretAccessKey"], "not a secret key")
            self.assertEqual(KMS_PROVIDERS["azure"]["tenantId"], "not a tenant ID")
            self.assertEqual(KMS_PROVIDERS["azure"]["clientId"], "not a client ID")
            self.assertEqual(KMS_PROVIDERS["azure"]["clientSecret"], "not a client secret")
            self.assertEqual(KMS_PROVIDERS["gcp"]["email"], "not an email")
            self.assertEqual(
                base64.b64decode(KMS_PROVIDERS["gcp"]["privateKey"]), b"not a private key"
            )
            self.assertEqual(KMS_PROVIDERS["kmip"]["endpoint"], "not a valid endpoint")
            self.assertIsInstance(KMS_PROVIDERS["local"]["key"], bytes)
            self.assertEqual(len(KMS_PROVIDERS["local"]["key"]), 96)

    def test_kms_credentials_env(self):
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
            kms_mod = self.reload_encryption_module()
            KMS_CREDENTIALS = kms_mod.KMS_CREDENTIALS

            self.assertEqual(KMS_CREDENTIALS["aws"]["key"], "TestArn")
            self.assertEqual(KMS_CREDENTIALS["aws"]["region"], "us-x-test")
            self.assertEqual(KMS_CREDENTIALS["azure"]["keyName"], "azure-key")
            self.assertEqual(
                KMS_CREDENTIALS["azure"]["keyVaultEndpoint"], "https://example.vault.azure.net/"
            )
            self.assertEqual(KMS_CREDENTIALS["gcp"]["projectId"], "gcp-test-prj")
            self.assertEqual(KMS_CREDENTIALS["gcp"]["location"], "test-loc")
            self.assertEqual(KMS_CREDENTIALS["gcp"]["keyRing"], "ring1")
            self.assertEqual(KMS_CREDENTIALS["gcp"]["keyName"], "gcp-key")

    def test_kms_providers_env(self):
        env = {
            "AWS_ACCESS_KEY_ID": "AKIAFAKE",
            "AWS_SECRET_ACCESS_KEY": "SECRETFAKE",
            "AZURE_TENANT_ID": "tenant-123",
            "AZURE_CLIENT_ID": "client-456",
            "AZURE_CLIENT_SECRET": "secret-xyz",
            "GCP_EMAIL": "my@google.key",
            "GCP_PRIVATE_KEY": base64.b64encode(b"keydata").decode("ascii"),
            "KMIP_KMS_ENDPOINT": "kmip://loc",
        }
        with patch.dict(os.environ, env, clear=True):
            kms_mod = self.reload_encryption_module()
            KMS_PROVIDERS = kms_mod.KMS_PROVIDERS

            self.assertEqual(KMS_PROVIDERS["aws"]["accessKeyId"], "AKIAFAKE")
            self.assertEqual(KMS_PROVIDERS["aws"]["secretAccessKey"], "SECRETFAKE")
            self.assertEqual(KMS_PROVIDERS["azure"]["tenantId"], "tenant-123")
            self.assertEqual(KMS_PROVIDERS["azure"]["clientId"], "client-456")
            self.assertEqual(KMS_PROVIDERS["azure"]["clientSecret"], "secret-xyz")
            self.assertEqual(KMS_PROVIDERS["gcp"]["email"], "my@google.key")
            self.assertEqual(base64.b64decode(KMS_PROVIDERS["gcp"]["privateKey"]), b"keydata")
            self.assertEqual(KMS_PROVIDERS["kmip"]["endpoint"], "kmip://loc")
            self.assertIsInstance(KMS_PROVIDERS["local"]["key"], bytes)
            self.assertEqual(len(KMS_PROVIDERS["local"]["key"]), 96)
