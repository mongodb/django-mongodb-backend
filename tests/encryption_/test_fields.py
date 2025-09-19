import datetime
from decimal import Decimal

from django.test import TestCase, skipUnlessDBFeature

from .models import (
    Billing,
    EncryptedBigIntegerTest,
    EncryptedBinaryTest,
    EncryptedBooleanTest,
    EncryptedCharTest,
    EncryptedDateTest,
    EncryptedDateTimeTest,
    EncryptedDecimalTest,
    EncryptedDurationTest,
    EncryptedEmailTest,
    EncryptedFloatTest,
    EncryptedGenericIPAddressTest,
    EncryptedIntegerTest,
    EncryptedPositiveBigIntegerTest,
    EncryptedPositiveIntegerTest,
    EncryptedPositiveSmallIntegerTest,
    EncryptedSmallIntegerTest,
    EncryptedTextTest,
    EncryptedTimeTest,
    EncryptedURLTest,
    Patient,
    PatientRecord,
)


class PatientModelTests(TestCase):
    def setUp(self):
        self.billing = Billing(cc_type="Visa", cc_number="4111111111111111")
        self.patient_record = PatientRecord(ssn="123-45-6789", billing=self.billing)
        self.patient = Patient.objects.create(
            patient_name="John Doe", patient_id=123456789, patient_record=self.patient_record
        )

    def test_patient_record_content(self):
        """Embedded patient record data should be stored and retrieved correctly."""
        patient = Patient.objects.get(id=self.patient.id)
        self.assertEqual(patient.patient_record.ssn, "123-45-6789")

    def test_billing_information(self):
        """Billing data inside the encrypted embedded model should be correct."""
        patient = Patient.objects.get(id=self.patient.id)
        self.assertEqual(patient.patient_record.billing.cc_type, "Visa")
        self.assertEqual(patient.patient_record.billing.cc_number, "4111111111111111")


@skipUnlessDBFeature("supports_queryable_encryption")
class EncryptedFieldTests(TestCase):
    databases = {"default", "encrypted"}

    def _assert_equality(self, model_cls, val):
        model_cls.objects.create(value=val)
        fetched = model_cls.objects.get(value=val)
        self.assertEqual(fetched.value, val)

    def _assert_range(self, model_cls, low, high, threshold):
        model_cls.objects.create(value=low)
        model_cls.objects.create(value=high)
        # equality check for both
        self.assertEqual(model_cls.objects.get(value=low).value, low)
        self.assertEqual(model_cls.objects.get(value=high).value, high)
        # range check using Python-side length (avoid unsupported count aggregation)
        objs = list(model_cls.objects.filter(value__gt=threshold))
        self.assertEqual(len(objs), 1)
        self.assertEqual(objs[0].value, high)

    # Equality-only fields
    def test_binary(self):
        self._assert_equality(EncryptedBinaryTest, b"\x00\x01\x02")

    def test_boolean(self):
        self._assert_equality(EncryptedBooleanTest, True)

    def test_char(self):
        self._assert_equality(EncryptedCharTest, "hello")

    def test_email(self):
        self._assert_equality(EncryptedEmailTest, "test@example.com")

    def test_ip(self):
        self._assert_equality(EncryptedGenericIPAddressTest, "192.168.0.1")

    def test_text(self):
        self._assert_equality(EncryptedTextTest, "some text")

    def test_url(self):
        self._assert_equality(EncryptedURLTest, "https://example.com")

    # Range fields
    def test_big_integer(self):
        self._assert_range(EncryptedBigIntegerTest, 100, 200, 150)

    def test_date(self):
        d1 = datetime.date(2024, 6, 1)
        d2 = datetime.date(2024, 6, 10)
        self._assert_range(EncryptedDateTest, d1, d2, datetime.date(2024, 6, 5))

    def test_datetime(self):
        dt1 = datetime.datetime(2024, 6, 1, 12, 0)
        dt2 = datetime.datetime(2024, 6, 2, 12, 0)
        self._assert_range(EncryptedDateTimeTest, dt1, dt2, datetime.datetime(2024, 6, 2, 0, 0))

    def test_decimal(self):
        self._assert_range(
            EncryptedDecimalTest, Decimal("123.45"), Decimal("200.50"), Decimal("150")
        )

    def test_duration(self):
        self._assert_range(
            EncryptedDurationTest,
            datetime.timedelta(days=3),
            datetime.timedelta(days=10),
            datetime.timedelta(days=5),
        )

    def test_float(self):
        self._assert_range(EncryptedFloatTest, 1.23, 4.56, 3.0)

    def test_integer(self):
        self._assert_range(EncryptedIntegerTest, 5, 10, 7)

    def test_positive_big_integer(self):
        self._assert_range(EncryptedPositiveBigIntegerTest, 100, 500, 200)

    def test_positive_integer(self):
        self._assert_range(EncryptedPositiveIntegerTest, 10, 20, 15)

    def test_positive_small_integer(self):
        self._assert_range(EncryptedPositiveSmallIntegerTest, 5, 8, 6)

    def test_small_integer(self):
        self._assert_range(EncryptedSmallIntegerTest, -5, 2, 0)

    def test_time(self):
        t1 = datetime.time(10, 0)
        t2 = datetime.time(15, 0)
        self._assert_range(EncryptedTimeTest, t1, t2, datetime.time(12, 0))
