import importlib
from datetime import datetime, time
from io import StringIO
from unittest.mock import patch

import pymongo
from bson import json_util
from bson.binary import Binary
from django.core.management import call_command
from django.db import connections, models
from django.test import TransactionTestCase, modify_settings, override_settings

from django_mongodb_backend.fields import EncryptedFieldMixin

from .models import (
    Appointment,
    Billing,
    EncryptedNumbers,
    Patient,
    PatientPortalUser,
    PatientRecord,
)
from .routers import TestEncryptedRouter

EXPECTED_ENCRYPTED_FIELDS_MAP = {
    "encryption__billing": {
        "fields": [
            {
                "bsonType": "string",
                "path": "cc_type",
                "queries": {"queryType": "equality"},
                "keyId": Binary(b" \x901\x89\x1f\xafAX\x9b*\xb1\xc7\xc5\xfdl\xa4", 4),
            },
            {
                "bsonType": "long",
                "path": "cc_number",
                "queries": {"queryType": "equality"},
                "keyId": Binary(b"\x97\xb4\x9d\xb8\xd5\xa6Ay\x85\xfe\x00\xc0\xd4{\xa2\xff", 4),
            },
            {
                "bsonType": "decimal",
                "path": "account_balance",
                "queries": {"queryType": "range"},
                "keyId": Binary(b"\xcc\x01-s\xea\xd9B\x8d\x80\xd7\xf8!n\xc6\xf5U", 4),
            },
        ]
    },
    "encryption__patientrecord": {
        "fields": [
            {
                "bsonType": "string",
                "path": "ssn",
                "queries": {"queryType": "equality"},
                "keyId": Binary(b"\x14F\x89\xde\x8d\x04K7\xa9\x9a\xaf_\xca\x8a\xfb&", 4),
            },
            {
                "bsonType": "date",
                "path": "birth_date",
                "queries": {"queryType": "range"},
                "keyId": Binary(b"@\xdd\xb4\xd2%\xc2B\x94\xb5\x07\xbc(ER[s", 4),
            },
            {
                "bsonType": "binData",
                "path": "profile_picture",
                "queries": {"queryType": "equality"},
                "keyId": Binary(b"Q\xa2\xebc!\xecD,\x8b\xe4$\xb6ul9\x9a", 4),
            },
            {
                "bsonType": "int",
                "path": "patient_age",
                "queries": {"queryType": "range"},
                "keyId": Binary(b"\ro\x80\x1e\x8e1K\xde\xbc_\xc3bi\x95\xa6j", 4),
            },
            {
                "bsonType": "double",
                "path": "weight",
                "queries": {"queryType": "range"},
                "keyId": Binary(b"\x9b\xfd:n\xe1\xd0N\xdd\xb3\xe7e)\x06\xea\x8a\x1d", 4),
            },
        ]
    },
    "encryption__patient": {
        "fields": [
            {
                "bsonType": "int",
                "path": "patient_id",
                "queries": {"queryType": "equality"},
                "keyId": Binary(b"\x8ft\x16:\x8a\x91D\xc7\x8a\xdf\xe5O\n[\xfd\\", 4),
            },
            {
                "bsonType": "string",
                "path": "patient_name",
                "keyId": Binary(b"<\x9b\xba\xeb:\xa4@m\x93\x0e\x0c\xcaN\x03\xfb\x05", 4),
            },
            {
                "bsonType": "string",
                "path": "patient_notes",
                "queries": {"queryType": "equality"},
                "keyId": Binary(b"\x01\xe7\xd1isnB$\xa9(gwO\xca\x10\xbd", 4),
            },
            {
                "bsonType": "date",
                "path": "registration_date",
                "queries": {"queryType": "equality"},
                "keyId": Binary(b"F\xfb\xae\x82\xd5\x9a@\xee\xbfJ\xaf#\x9c:-I", 4),
            },
            {
                "bsonType": "bool",
                "path": "is_active",
                "queries": {"queryType": "equality"},
                "keyId": Binary(b"\xb2\xb5\xc4K53A\xda\xb9V\xa6\xa9\x97\x94\xea;", 4),
            },
        ]
    },
}


class EncryptedDurationField(EncryptedFieldMixin, models.DurationField):
    """
    Unsupported by MongoDB when used with Queryable Encryption.
    Included in tests until fix or wontfix.
    """


class EncryptedSlugField(EncryptedFieldMixin, models.SlugField):
    """
    Unsupported by MongoDB when used with Queryable Encryption.
    Included in tests until fix or wontfix.
    """


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
class EncryptedFieldTests(TransactionTestCase):
    databases = {"default", "other"}
    available_apps = ["django_mongodb_backend", "encryption_"]

    def setUp(self):
        self.appointment = Appointment(time="8:00")
        self.appointment.save()

        self.billing = Billing(cc_type="Visa", cc_number=1234567890123456, account_balance=100.50)
        self.billing.save()

        self.portal_user = PatientPortalUser(
            ip_address="127.0.0.1",
            url="https://example.com",
        )
        self.portal_user.save()

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
            email="john.doe@example.com",
        )
        self.patient.save()

        # TODO: Embed billing and patient_record models in patient model then add tests

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        try:
            from pymongo_auth_aws.auth import AwsCredential  # noqa: PLC0415
        except ImportError:
            cls.skipTest(cls, "pymongo_auth_aws not installed, skipping AWS credentials tests")

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

    def test_get_encrypted_fields_map(self):
        """Test class method called by schema editor
        and management command to get encrypted fields map for
        `create_encrypted_collection` and `auto_encryption_opts` respectively.
        There are no data keys in the results.

        Data keys for the schema editor are created by
        `create_encrypted_collection` and data keys for the
        management command are created by the management command
        using code similar to the code in `create_encrypted_collection`
        in Pymongo.
        """
        expected_encrypted_fields_map = {
            "encryption__patient": {
                "fields": [
                    {
                        "bsonType": "int",
                        "path": "patient_id",
                        "queries": {"queryType": "equality"},
                    },
                    {
                        "bsonType": "string",
                        "path": "patient_name",
                    },
                    {
                        "bsonType": "string",
                        "path": "patient_notes",
                        "queries": {"queryType": "equality"},
                    },
                    {
                        "bsonType": "date",
                        "path": "registration_date",
                        "queries": {"queryType": "equality"},
                    },
                    {
                        "bsonType": "bool",
                        "path": "is_active",
                        "queries": {"queryType": "equality"},
                    },
                    {
                        "bsonType": "string",
                        "path": "email",
                        "queries": {"queryType": "equality"},
                    },
                ]
            },
        }
        self.maxDiff = None
        with connections["other"].schema_editor() as editor:
            db_table = self.patient._meta.db_table
            self.assertEqual(
                editor._get_encrypted_fields_map(self.patient),
                expected_encrypted_fields_map[db_table],
            )

    def test_show_schema_map(self):
        self.maxDiff = None
        out = StringIO()
        call_command(
            "showschemamap",
            "--database",
            "other",
            verbosity=0,
            stdout=out,
        )
        self.assertEqual(json_util.dumps(EXPECTED_ENCRYPTED_FIELDS_MAP, indent=2), out.getvalue())

    def test_set_encrypted_fields_map_in_client(self):
        # TODO: Create new client with and without schema map provided then
        # sync database to ensure encrypted collections are created in both
        pass

    def test_appointment(self):
        self.assertEqual(Appointment.objects.get(time="8:00").time, time(8, 0))

    def test_billing(self):
        self.assertEqual(
            Billing.objects.get(cc_number=1234567890123456).cc_number, 1234567890123456
        )
        self.assertEqual(Billing.objects.get(cc_type="Visa").cc_type, "Visa")
        self.assertTrue(Billing.objects.filter(account_balance__gte=100.0).exists())

    def test_patientportaluser(self):
        self.assertEqual(
            PatientPortalUser.objects.get(ip_address="127.0.0.1").ip_address, "127.0.0.1"
        )

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

        # Test encrypted patient record in unencrypted database.
        conn_params = connections["other"].get_connection_params()
        if conn_params.pop("auto_encryption_opts", False):
            # Call MongoClient instead of get_new_connection because
            # get_new_connection will return the encrypted connection
            # from the connection pool.
            connection = pymongo.MongoClient(**conn_params)
            patientrecords = connection["test_other"].encryption__patientrecord.find()
            ssn = patientrecords[0]["ssn"]
            self.assertTrue(isinstance(ssn, Binary))
            connection.close()

    def test_patient(self):
        self.assertEqual(
            Patient.objects.get(patient_notes="patient notes " * 25).patient_notes,
            "patient notes " * 25,
        )
        self.assertEqual(
            Patient.objects.get(
                registration_date=datetime(2023, 10, 1, 12, 0, 0)
            ).registration_date,
            datetime(2023, 10, 1, 12, 0, 0),
        )
        self.assertTrue(Patient.objects.get(patient_id=1).is_active)
        self.assertEqual(
            Patient.objects.get(email="john.doe@example.com").email, "john.doe@example.com"
        )

        # Test decrypted patient record in encrypted database.
        patients = connections["other"].database.encryption__patient.find()
        self.assertEqual(len(list(patients)), 1)
        records = connections["other"].database.encryption__patientrecord.find()
        self.assertTrue("__safeContent__" in records[0])


class EncryptedNumberFieldTests(EncryptedFieldTests):
    def test_create_and_query(self):
        EncryptedNumbers.objects.create(
            pos_bigint=1000000,
            # FIXME: pymongo.errors.EncryptionError: Cannot encrypt element of type int
            # because schema requires that type is one of: [ long ]
            # pos_int=1,
            pos_smallint=12345,
            smallint=-12345,
        )

        obj = EncryptedNumbers.objects.get(pos_bigint=1000000)
        # obj = EncryptedNumbers.objects.get(pos_int=1)
        obj = EncryptedNumbers.objects.get(pos_smallint=12345)
        obj = EncryptedNumbers.objects.get(smallint=-12345)

        self.assertEqual(obj.pos_bigint, 1000000)
        # self.assertEqual(obj.pos_int, 1)
        self.assertEqual(obj.pos_smallint, 12345)
        self.assertEqual(obj.smallint, -12345)
