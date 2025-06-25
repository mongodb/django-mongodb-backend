import datetime
import uuid
from decimal import Decimal

from bson import ObjectId

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


class ArrayModelTests(EncryptionTestCase):
    def setUp(self):
        self.array_model = ArrayModel.objects.create(values=[1, 2, 3, 4, 5])

    def test_array(self):
        array_model = ArrayModel.objects.get(id=self.array_model.id)
        self.assertEqual(array_model.values, [1, 2, 3, 4, 5])
        self.assertEncrypted(self.array_model, "values")


class EmbeddedModelTests(EncryptionTestCase):
    def setUp(self):
        self.billing = Billing(cc_type="Visa", cc_number="4111111111111111")
        self.patient_record = PatientRecord(ssn="123-45-6789", billing=self.billing)
        self.patient = Patient.objects.create(
            patient_name="John Doe", patient_id=123456789, patient_record=self.patient_record
        )

    def test_object(self):
        patient = Patient.objects.get(id=self.patient.id)
        self.assertEqual(patient.patient_record.ssn, "123-45-6789")
        self.assertEqual(patient.patient_record.billing.cc_type, "Visa")
        self.assertEqual(patient.patient_record.billing.cc_number, "4111111111111111")


class EmbeddedModelArrayTests(EncryptionTestCase):
    def setUp(self):
        self.actor1 = Actor(name="Actor One")
        self.actor2 = Actor(name="Actor Two")
        self.movie = Movie.objects.create(
            title="Sample Movie",
            cast=[self.actor1, self.actor2],
            released=datetime.date(2024, 6, 1),
        )

    def test_array(self):
        movie = Movie.objects.get(id=self.movie.id)
        self.assertEqual(len(movie.cast), 2)
        self.assertEqual(movie.cast[0].name, "Actor One")
        self.assertEqual(movie.cast[1].name, "Actor Two")
        self.assertEncrypted(movie, "cast")


class FieldTests(EncryptionTestCase):
    def assertEquality(self, model_cls, val):
        model_cls.objects.create(value=val)
        fetched = model_cls.objects.get(value=val)
        self.assertEqual(fetched.value, val)

    def assertRange(self, model_cls, *, low, high, threshold):
        model_cls.objects.create(value=low)
        model_cls.objects.create(value=high)
        self.assertEqual(model_cls.objects.get(value=low).value, low)
        self.assertEqual(model_cls.objects.get(value=high).value, high)
        objs = list(model_cls.objects.filter(value__gt=threshold))
        self.assertEqual(len(objs), 1)
        self.assertEqual(objs[0].value, high)

    # Equality-only fields
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

    def test_ip(self):
        self.assertEquality(GenericIPAddressModel, "192.168.0.1")
        self.assertEncrypted(GenericIPAddressModel, "value")

    def test_objectid(self):
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

    # Range fields
    def test_big_integer(self):
        self.assertRange(BigIntegerModel, low=100, high=200, threshold=150)
        self.assertEncrypted(BigIntegerModel, "value")

    def test_date(self):
        self.assertRange(
            DateModel,
            low=datetime.date(2024, 6, 1),
            high=datetime.date(2024, 6, 10),
            threshold=datetime.date(2024, 6, 5),
        )
        self.assertEncrypted(DateModel, "value")

    def test_datetime(self):
        self.assertRange(
            DateTimeModel,
            low=datetime.datetime(2024, 6, 1, 12, 0),
            high=datetime.datetime(2024, 6, 2, 12, 0),
            threshold=datetime.datetime(2024, 6, 2, 0, 0),
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
            low=datetime.timedelta(days=3),
            high=datetime.timedelta(days=10),
            threshold=datetime.timedelta(days=5),
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
            low=datetime.time(10, 0),
            high=datetime.time(15, 0),
            threshold=datetime.time(12, 0),
        )
        self.assertEncrypted(TimeModel, "value")


class FieldMixinTests(EncryptionTestCase):
    def test_db_index(self):
        msg = "'db_index=True' is not supported on encrypted fields."
        with self.assertRaisesMessage(ValueError, msg):
            EncryptedIntegerField(db_index=True)

    def test_null(self):
        msg = "'null=True' is not supported on encrypted fields."
        with self.assertRaisesMessage(ValueError, msg):
            EncryptedIntegerField(null=True)

    def test_unique(self):
        msg = "'unique=True' is not supported on encrypted fields."
        with self.assertRaisesMessage(ValueError, msg):
            EncryptedIntegerField(unique=True)

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
