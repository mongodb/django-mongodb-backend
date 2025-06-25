from datetime import datetime

from django.test import TransactionTestCase, override_settings, skipUnlessDBFeature

from .models import (
    Appointment,
    Billing,
    Patient,
    PatientPortalUser,
    PatientRecord,
)
from .routers import TestEncryptedRouter


@skipUnlessDBFeature("supports_queryable_encryption")
@override_settings(DATABASE_ROUTERS=[TestEncryptedRouter()])
class QueryableEncryptionTestCase(TransactionTestCase):
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
