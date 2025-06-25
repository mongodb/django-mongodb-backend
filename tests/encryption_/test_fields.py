import uuid
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from bson import ObjectId
from django.db import DatabaseError
from django.db.models import F, Q
from django.test import SimpleTestCase

from django_mongodb_backend.fields import (
    EncryptedArrayField,
    EncryptedCharField,
    EncryptedEmbeddedModelArrayField,
    EncryptedEmbeddedModelField,
    EncryptedIntegerField,
)

from .models import (
    Actor,
    ArrayModel,
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
    Movie,
    ObjectIdModel,
    Patient,
    PatientRecord,
    PositiveBigIntegerModel,
    PositiveIntegerModel,
    PositiveSmallIntegerModel,
    SmallIntegerModel,
    TextModel,
    TimeModel,
    URLModel,
    UUIDModel,
)
from .test_base import EncryptionTestCase


class FieldTests(EncryptionTestCase):
    def assertEquality(self, model_cls, val):
        obj = model_cls.objects.create(value=val)
        self.assertEqual(model_cls.objects.get(value=val), obj)
        self.assertEqual(model_cls.objects.get(value__in=[val]), obj)
        self.assertQuerySetEqual(model_cls.objects.exclude(value=val), [])

    def assertRange(self, model_cls, *, low, high, threshold):
        obj1 = model_cls.objects.create(value=low)
        obj2 = model_cls.objects.create(value=high)
        self.assertEqual(model_cls.objects.get(value=low).value, low)
        self.assertEqual(model_cls.objects.get(value=high).value, high)
        self.assertEqual(model_cls.objects.exclude(value=high).get().value, low)
        self.assertCountEqual(model_cls.objects.filter(Q(value=high) | Q(value=low)), [obj1, obj2])
        self.assertCountEqual(model_cls.objects.filter(value__gt=threshold), [obj2])
        self.assertCountEqual(model_cls.objects.filter(value__gte=threshold), [obj2])
        self.assertCountEqual(model_cls.objects.filter(value__lt=threshold), [obj1])
        self.assertCountEqual(model_cls.objects.filter(value__lte=threshold), [obj1])
        self.assertCountEqual(model_cls.objects.filter(value__in=[low]), [obj1])
        self.assertCountEqual(model_cls.objects.filter(value__range=[low, high]), [obj1, obj2])
        msg = (
            "Comparison disallowed between Queryable Encryption encrypted "
            "fields and non-constant expressions; field 'value' is encrypted."
        )
        with self.assertRaisesMessage(DatabaseError, msg):
            model_cls.objects.filter(value__lte=F("value")).get()

    def test_array(self):
        obj = ArrayModel.objects.create(values=[1, 2, 3, 4, 5])
        obj.refresh_from_db()
        self.assertEqual(obj.values, [1, 2, 3, 4, 5])
        self.assertEncrypted(obj, "values")

    def test_embedded_model(self):
        patient = Patient.objects.create(
            patient_name="John Doe",
            patient_id=123456789,
            patient_record=PatientRecord(
                ssn="123-45-6789",
                billing=Billing(cc_type="Visa", cc_number="4111111111111111"),
            ),
        )
        patient.refresh_from_db()
        self.assertEqual(patient.patient_record.ssn, "123-45-6789")
        self.assertEqual(patient.patient_record.billing.cc_type, "Visa")
        self.assertEqual(patient.patient_record.billing.cc_number, "4111111111111111")
        self.assertEncrypted(patient, "patient_record.billing")
        self.assertEncrypted(patient, "patient_record.ssn")
        # Encrypted embedded fields are queryable.
        self.assertEqual(Patient.objects.get(patient_record__ssn="123-45-6789"), patient)

    def test_encrypted_embedded_model_field_subfields_not_queryable(self):
        """Subfields of EncryptedEmbeddedModelField aren't queryable."""
        msg = (
            "Invalid operation on path 'patient_record.billing.cc_type' which "
            "contains an encrypted path prefix."
        )
        with self.assertRaisesMessage(DatabaseError, msg):
            Patient.objects.get(patient_record__billing__cc_type="Visa")

    def test_embedded_model_array(self):
        movie = Movie.objects.create(
            title="Sample Movie",
            cast=[Actor(name="Harrison"), Actor(name="James")],
        )
        movie.refresh_from_db()
        self.assertEqual(len(movie.cast), 2)
        self.assertEqual(movie.cast[0].name, "Harrison")
        self.assertEqual(movie.cast[1].name, "James")
        self.assertEncrypted(movie, "cast")

    # Equality queries
    def test_binary(self):
        self.assertEquality(BinaryModel, b"\x00\x01\x02")
        self.assertEncrypted(BinaryModel, "value")

    def test_boolean(self):
        self.assertEquality(BooleanModel, True)
        self.assertEncrypted(BooleanModel, "value")

    def test_char(self):
        self.assertEquality(CharModel, "hello")
        self.assertEncrypted(CharModel, "value")

    def test_email(self):
        self.assertEquality(EmailModel, "test@example.com")
        self.assertEncrypted(EmailModel, "value")

    def test_generic_ip_address(self):
        self.assertEquality(GenericIPAddressModel, "192.168.0.1")
        self.assertEncrypted(GenericIPAddressModel, "value")

    def test_object_id(self):
        self.assertEquality(ObjectIdModel, ObjectId())
        self.assertEncrypted(ObjectIdModel, "value")

    def test_text(self):
        self.assertEquality(TextModel, "some text")
        self.assertEncrypted(TextModel, "value")

    def test_url(self):
        self.assertEquality(URLModel, "https://example.com")
        self.assertEncrypted(URLModel, "value")

    def test_uuid(self):
        self.assertEquality(UUIDModel, uuid.uuid4())
        self.assertEncrypted(UUIDModel, "value")

    # Range queries
    def test_big_integer(self):
        self.assertRange(BigIntegerModel, low=100, high=200, threshold=150)
        self.assertEncrypted(BigIntegerModel, "value")

    def test_date(self):
        self.assertRange(
            DateModel,
            low=date(2024, 6, 1),
            high=date(2024, 6, 10),
            threshold=date(2024, 6, 5),
        )
        self.assertEncrypted(DateModel, "value")

    def test_date_time(self):
        self.assertRange(
            DateTimeModel,
            low=datetime(2024, 6, 1, 12, 0),
            high=datetime(2024, 6, 2, 12, 0),
            threshold=datetime(2024, 6, 2, 0, 0),
        )
        self.assertEncrypted(DateTimeModel, "value")

    def test_decimal(self):
        self.assertRange(
            DecimalModel,
            low=Decimal("123.45"),
            high=Decimal("200.50"),
            threshold=Decimal("150"),
        )
        self.assertEncrypted(DecimalModel, "value")

    def test_duration(self):
        self.assertRange(
            DurationModel,
            low=timedelta(days=3),
            high=timedelta(days=10),
            threshold=timedelta(days=5),
        )
        self.assertEncrypted(DurationModel, "value")

    def test_float(self):
        self.assertRange(FloatModel, low=1.23, high=4.56, threshold=3.0)
        self.assertEncrypted(FloatModel, "value")

    def test_integer(self):
        self.assertRange(IntegerModel, low=5, high=10, threshold=7)
        self.assertEncrypted(IntegerModel, "value")

    def test_positive_big_integer(self):
        self.assertRange(PositiveBigIntegerModel, low=100, high=500, threshold=200)
        self.assertEncrypted(PositiveBigIntegerModel, "value")

    def test_positive_integer(self):
        self.assertRange(PositiveIntegerModel, low=10, high=20, threshold=15)
        self.assertEncrypted(PositiveIntegerModel, "value")

    def test_positive_small_integer(self):
        self.assertRange(PositiveSmallIntegerModel, low=5, high=8, threshold=6)
        self.assertEncrypted(PositiveSmallIntegerModel, "value")

    def test_small_integer(self):
        self.assertRange(SmallIntegerModel, low=-5, high=2, threshold=0)
        self.assertEncrypted(SmallIntegerModel, "value")

    def test_time(self):
        self.assertRange(
            TimeModel,
            low=time(10, 0),
            high=time(15, 0),
            threshold=time(12, 0),
        )
        self.assertEncrypted(TimeModel, "value")


class FieldMixinTests(SimpleTestCase):
    def test_db_index(self):
        msg = "Encrypted fields do not support db_index=True."
        with self.assertRaisesMessage(ValueError, msg):
            EncryptedIntegerField(db_index=True)

    def test_null(self):
        msg = "Encrypted fields do not support null=True."
        with self.assertRaisesMessage(ValueError, msg):
            EncryptedIntegerField(null=True)

    def test_unique(self):
        msg = "Encrypted fields do not support unique=True."
        with self.assertRaisesMessage(ValueError, msg):
            EncryptedIntegerField(unique=True)

    def test_deconstruct(self):
        field = EncryptedCharField(max_length=50, queries={"field": "value"})
        field.name = "ssn"
        name, path, args, kwargs = field.deconstruct()
        self.assertEqual(name, "ssn")
        self.assertEqual(path, "django_mongodb_backend.fields.EncryptedCharField")
        self.assertEqual(args, [])
        self.assertEqual(kwargs["queries"], {"field": "value"})

    def test_fields_without_queries(self):
        """Some field types (array, object) can't be queried."""
        for field in (
            EncryptedArrayField,
            EncryptedEmbeddedModelField,
            EncryptedEmbeddedModelArrayField,
        ):
            with self.subTest(field=field):
                msg = f"{field.__name__} does not support the queries argument."
                with self.assertRaisesMessage(ValueError, msg):
                    field(Actor, queries={})
