from datetime import date, datetime, time, timedelta

import pymongo
from bson.binary import Binary
from django.conf import settings
from django.db import connections

from django_mongodb_backend.fields import EncryptedFieldMixin

from .models import (
    Appointment,
    Billing,
    CreditCard,
    Patient,
    PatientPortalUser,
    PatientRecord,
)
from .test_base import QueryableEncryptionTestCase


class FieldTests(QueryableEncryptionTestCase):
    def setUp(self):
        Patient.objects.create(
            patient_id=1,
            full_name="John Doe",
            notes="patient notes " * 25,
            registration_date=datetime(2023, 10, 1, 12, 0, 0),
            is_active=True,
            contact_email="john.doe@example.com",
        )
        PatientRecord.objects.create(
            ssn="123-45-6789",
            birth_date="1969-01-01",
            profile_picture_data=b"image data",
            age=50,
            weight=180.0,
            insurance_policy_number=98765432101234,
            emergency_contacts_count=2,
            completed_visits=3,
        )
        Billing.objects.create(
            account_balance=100.50,
            payment_duration=timedelta(days=30),
        )
        CreditCard.objects.create(
            card_type="Visa",
            card_number=1234567890123456,
            transaction_reference=98765432101234,
        )
        Appointment.objects.create(start_time="8:00")
        PatientPortalUser.objects.create(
            last_login_ip="127.0.0.1", profile_url="https://example.com"
        )

    def test_binaryfield(self):
        self.assertEqual(
            PatientRecord.objects.get(profile_picture_data=b"image data").profile_picture_data,
            b"image data",
        )

    def test_booleanfield(self):
        self.assertTrue(Patient.objects.get(patient_id=1).is_active)

    def test_charfield(self):
        self.assertEqual(CreditCard.objects.get(card_type="Visa").card_type, "Visa")
        self.assertEqual(PatientRecord.objects.get(ssn="123-45-6789").ssn, "123-45-6789")

    def test_datefield(self):
        self.assertEqual(
            PatientRecord.objects.get(birth_date="1969-1-1").birth_date, date(1969, 1, 1)
        )

    def test_datetimefield(self):
        self.assertEqual(
            Patient.objects.get(
                registration_date=datetime(2023, 10, 1, 12, 0, 0)
            ).registration_date,
            datetime(2023, 10, 1, 12, 0, 0),
        )

    def test_decimalfield(self):
        self.assertTrue(Billing.objects.filter(account_balance__gte=100.0).exists())

    def test_durationfield(self):
        self.assertTrue(Billing.objects.filter(payment_duration__gte=timedelta(days=15)).exists())

    def test_emailfield(self):
        self.assertEqual(
            Patient.objects.get(contact_email="john.doe@example.com").contact_email,
            "john.doe@example.com",
        )

    def test_floatfield(self):
        self.assertTrue(PatientRecord.objects.filter(weight__gte=175.0).exists())

    def test_integerfield(self):
        self.assertEqual(
            CreditCard.objects.get(card_number=1234567890123456).card_number, 1234567890123456
        )
        self.assertEqual(
            PatientRecord.objects.get(emergency_contacts_count=2).emergency_contacts_count, 2
        )

    def test_positive_bigintegerfield(self):
        self.assertEqual(
            PatientRecord.objects.get(
                insurance_policy_number=98765432101234
            ).insurance_policy_number,
            98765432101234,
        )

    def test_positive_integerfield(self):
        self.assertEqual(
            PatientRecord.objects.get(emergency_contacts_count=2).emergency_contacts_count, 2
        )

    def test_positive_smallintegerfield(self):
        self.assertEqual(PatientRecord.objects.get(completed_visits=3).completed_visits, 3)

    def test_bigintegerfield(self):
        self.assertEqual(
            CreditCard.objects.get(transaction_reference=98765432101234).transaction_reference,
            98765432101234,
        )

    def test_ipaddressfield(self):
        self.assertEqual(
            PatientPortalUser.objects.get(last_login_ip="127.0.0.1").last_login_ip, "127.0.0.1"
        )

    def test_smallintegerfield(self):
        self.assertTrue(PatientRecord.objects.filter(age__gte=40).exists())
        self.assertFalse(PatientRecord.objects.filter(age__gte=80).exists())

    def test_textfield(self):
        self.assertEqual(
            Patient.objects.get(notes="patient notes " * 25).notes,
            "patient notes " * 25,
        )

    def test_timefield(self):
        self.assertEqual(Appointment.objects.get(start_time="8:00").start_time, time(8, 0))

    def test_encrypted_patient_record_in_encrypted_database(self):
        patients = connections["encrypted"].database.encryption__patient.find()
        self.assertEqual(len(list(patients)), 1)
        records = connections["encrypted"].database.encryption__patientrecord.find()
        self.assertTrue("__safeContent__" in records[0])

    def test_encrypted_patient_record_in_unencrypted_database(self):
        conn_params = connections["encrypted"].get_connection_params()
        db_name = settings.DATABASES["encrypted"]["NAME"]
        if conn_params.pop("auto_encryption_opts", False):
            with pymongo.MongoClient(**conn_params) as new_connection:
                patientrecords = new_connection[db_name].encryption__patientrecord.find()
                ssn = patientrecords[0]["ssn"]
                self.assertTrue(isinstance(ssn, Binary))

    def test_encrypted_fields_cannot_be_null(self):
        class Field(EncryptedFieldMixin):
            pass

        msg = "'null=True' is not supported for encrypted fields."
        with self.assertRaisesMessage(ValueError, msg):
            Field(null=True)
