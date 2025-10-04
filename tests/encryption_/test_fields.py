import datetime
from decimal import Decimal

from django_mongodb_backend.fields import EncryptedCharField

from .models import (
    BigIntegerModel,
    Billing,
    BinaryModel,
    BooleanModel,
    CharModel,
    DateModel,
    DateTimeModel,
    DecimalModel,
    DurationModel,
    EmailModel,
    FloatModel,
    GenericIPAddressModel,
    IntegerModel,
    Patient,
    PatientRecord,
    PositiveBigIntegerModel,
    PositiveIntegerModel,
    PositiveSmallIntegerModel,
    SmallIntegerModel,
    TextModel,
    TimeModel,
    URLModel,
)
from .test_base import EncryptionTestCase


class PatientModelTests(EncryptionTestCase):
    def setUp(self):
        self.billing = Billing(cc_type="Visa", cc_number="4111111111111111")
        self.patient_record = PatientRecord(ssn="123-45-6789", billing=self.billing)
        self.patient = Patient.objects.create(
            patient_name="John Doe", patient_id=123456789, patient_record=self.patient_record
        )

    def test_patient(self):
        patient = Patient.objects.get(id=self.patient.id)
        self.assertEqual(patient.patient_record.ssn, "123-45-6789")
        self.assertEqual(patient.patient_record.billing.cc_type, "Visa")
        self.assertEqual(patient.patient_record.billing.cc_number, "4111111111111111")


class EncryptedFieldTests(EncryptionTestCase):
    def assertEquality(self, model_cls, val):
        model_cls.objects.create(value=val)
        fetched = model_cls.objects.get(value=val)
        self.assertEqual(fetched.value, val)

    def assertRange(self, model_cls, *, low, high, threshold):
        model_cls.objects.create(value=low)
        model_cls.objects.create(value=high)
        # equality check for both
        self.assertEqual(model_cls.objects.get(value=low).value, low)
        self.assertEqual(model_cls.objects.get(value=high).value, high)
        # range check using `len()` because MongoDB does not support
        # SQL-style COUNT aggregation and we can't rely on the queryset's
        # count() method
        objs = list(model_cls.objects.filter(value__gt=threshold))
        self.assertEqual(len(objs), 1)
        self.assertEqual(objs[0].value, high)

    # Equality-only fields
    def test_binary(self):
        self.assertEquality(BinaryModel, b"\x00\x01\x02")

    def test_boolean(self):
        self.assertEquality(BooleanModel, True)

    def test_char(self):
        self.assertEquality(CharModel, "hello")

    def test_email(self):
        self.assertEquality(EmailModel, "test@example.com")

    def test_ip(self):
        self.assertEquality(GenericIPAddressModel, "192.168.0.1")

    def test_text(self):
        self.assertEquality(TextModel, "some text")

    def test_url(self):
        self.assertEquality(URLModel, "https://example.com")

    # Range fields
    def test_big_integer(self):
        self.assertRange(BigIntegerModel, low=100, high=200, threshold=150)

    def test_date(self):
        self.assertRange(
            DateModel,
            low=datetime.date(2024, 6, 1),
            high=datetime.date(2024, 6, 10),
            threshold=datetime.date(2024, 6, 5),
        )

    def test_datetime(self):
        self.assertRange(
            DateTimeModel,
            low=datetime.datetime(2024, 6, 1, 12, 0),
            high=datetime.datetime(2024, 6, 2, 12, 0),
            threshold=datetime.datetime(2024, 6, 2, 0, 0),
        )

    def test_decimal(self):
        self.assertRange(
            DecimalModel,
            low=Decimal("123.45"),
            high=Decimal("200.50"),
            threshold=Decimal("150"),
        )

    def test_duration(self):
        self.assertRange(
            DurationModel,
            low=datetime.timedelta(days=3),
            high=datetime.timedelta(days=10),
            threshold=datetime.timedelta(days=5),
        )

    def test_float(self):
        self.assertRange(FloatModel, low=1.23, high=4.56, threshold=3.0)

    def test_integer(self):
        self.assertRange(IntegerModel, low=5, high=10, threshold=7)

    def test_positive_big_integer(self):
        self.assertRange(PositiveBigIntegerModel, low=100, high=500, threshold=200)

    def test_positive_integer(self):
        self.assertRange(PositiveIntegerModel, low=10, high=20, threshold=15)

    def test_positive_small_integer(self):
        self.assertRange(PositiveSmallIntegerModel, low=5, high=8, threshold=6)

    def test_small_integer(self):
        self.assertRange(SmallIntegerModel, low=-5, high=2, threshold=0)

    def test_time(self):
        self.assertRange(
            TimeModel,
            low=datetime.time(10, 0),
            high=datetime.time(15, 0),
            threshold=datetime.time(12, 0),
        )


class EncryptedFieldMixinTests(EncryptionTestCase):
    def test_null_true_raises_error(self):
        with self.assertRaisesMessage(
            ValueError, "'null=True' is not supported for encrypted fields."
        ):
            EncryptedCharField(max_length=50, null=True)

    def test_deconstruct_preserves_queries_and_rewrites_path(self):
        field = EncryptedCharField(max_length=50, queries={"field": "value"})
        field.name = "ssn"
        name, path, args, kwargs = field.deconstruct()

        # Name is preserved
        self.assertEqual(name, "ssn")

        # Path is rewritten from 'encrypted_model' to regular fields path
        self.assertEqual(path, "django_mongodb_backend.fields.EncryptedCharField")

        # No positional args for CharField
        self.assertEqual(args, [])

        # Queries value is preserved in kwargs
        self.assertIn("queries", kwargs)
        self.assertEqual(kwargs["queries"], {"field": "value"})

        # Reconstruct from deconstruct output
        new_field = EncryptedCharField(*args, **kwargs)

        # Reconstructed field is equivalent
        self.assertEqual(new_field.queries, field.queries)
        self.assertIsNot(new_field, field)
        self.assertEqual(new_field.max_length, field.max_length)
