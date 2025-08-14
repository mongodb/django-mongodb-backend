from datetime import datetime, time

import pymongo
from bson.binary import Binary
from django.conf import settings
from django.db import connections
from django.test import override_settings

from .models import (
    Appointment,
    Billing,
    EncryptedNumbers,
    Patient,
    PatientPortalUser,
    PatientRecord,
)
from .routers import TestEncryptedRouter
from .test_base import QueryableEncryptionTestCase


@override_settings(DATABASE_ROUTERS=[TestEncryptedRouter()])
class QueryableEncryptionFieldTests(QueryableEncryptionTestCase):
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

    def test_pos_small_int(self):
        obj = EncryptedNumbers.objects.get(pos_smallint=12345)
        self.assertEqual(obj.pos_smallint, 12345)

    def test_small_int(self):
        obj = EncryptedNumbers.objects.get(smallint=-12345)
        self.assertEqual(obj.smallint, -12345)
