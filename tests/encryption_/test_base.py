from datetime import datetime, time

import pymongo
from bson.binary import Binary
from django.conf import settings
from django.db import connections, models
from django.test import TransactionTestCase, override_settings

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


@override_settings(DATABASE_ROUTERS=[TestEncryptedRouter()])
class EncryptedFieldTests(TransactionTestCase):
    databases = {"default", "encrypted"}
    available_apps = ["encryption_"]

    def setUp(self):
        self.appointment = Appointment.objects.create(time="8:00")

        self.billing = Billing.objects.create(
            cc_type="Visa", cc_number=1234567890123456, account_balance=100.50
        )

        self.portal_user = PatientPortalUser.objects.create(
            ip_address="127.0.0.1",
            url="https://example.com",
        )

        self.patientrecord = PatientRecord.objects.create(
            ssn="123-45-6789",
            birth_date="1970-01-01",
            profile_picture=b"image data",
            weight=175.5,
            patient_age=47,
        )

        self.patient = Patient.objects.create(
            patient_id=1,
            patient_name="John Doe",
            patient_notes="patient notes " * 25,
            registration_date=datetime(2023, 10, 1, 12, 0, 0),
            is_active=True,
            email="john.doe@example.com",
        )

        # TODO: Embed billing and patient_record models in patient model
        # then add tests

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
        }
        connection = connections["encrypted"]
        auto_encryption_opts = getattr(connection.connection._options, "auto_encryption_opts", None)
        with connection.schema_editor() as editor:
            client = connection.connection
            encrypted_fields_map = editor._get_encrypted_fields_map(
                self.patient, client, auto_encryption_opts
            )
            for field in encrypted_fields_map["fields"]:
                # Remove data keys from the output; they are expected to differ
                field.pop("keyId", None)
            self.assertEqual(
                encrypted_fields_map,
                expected_encrypted_fields_map,
            )

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
        self.assertTrue(PatientRecord.objects.filter(patient_age__gte=40).exists())
        self.assertFalse(PatientRecord.objects.filter(patient_age__gte=80).exists())
        self.assertTrue(PatientRecord.objects.filter(weight__gte=175.0).exists())

        # Test encrypted patient record in unencrypted database.
        conn_params = connections["encrypted"].get_connection_params()
        db_name = settings.DATABASES["encrypted"]["NAME"]
        if conn_params.pop("auto_encryption_opts", False):
            # Call MongoClient instead of get_new_connection because
            # get_new_connection will return the encrypted connection
            # from the connection pool.
            with pymongo.MongoClient(**conn_params) as new_connection:
                patientrecords = new_connection[db_name].encryption__patientrecord.find()
                ssn = patientrecords[0]["ssn"]
                self.assertTrue(isinstance(ssn, Binary))

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
        patients = connections["encrypted"].database.encryption__patient.find()
        self.assertEqual(len(list(patients)), 1)
        records = connections["encrypted"].database.encryption__patientrecord.find()
        self.assertTrue("__safeContent__" in records[0])

    def test_numeric_fields(self):
        """
        Fields that have not been tested elsewhere.
        """
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
