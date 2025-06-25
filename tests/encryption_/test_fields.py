import datetime
import uuid
from decimal import Decimal
from operator import attrgetter

from bson import ObjectId
from django.db import DatabaseError
from django.db.models import Avg, Count, F, Q

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
    Author,
    BigIntegerModel,
    Billing,
    BinaryModel,
    Book,
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
        self.assertQuerySetEqual(
            model_cls.objects.filter(value__gt=threshold), [high], attrgetter("value")
        )
        self.assertQuerySetEqual(
            model_cls.objects.filter(value__gte=threshold), [high], attrgetter("value")
        )
        self.assertQuerySetEqual(
            model_cls.objects.filter(value__lt=threshold), [low], attrgetter("value")
        )
        self.assertQuerySetEqual(
            model_cls.objects.filter(value__lte=threshold), [low], attrgetter("value")
        )
        self.assertQuerySetEqual(
            model_cls.objects.filter(value__in=[low]), [low], attrgetter("value")
        )
        msg = (
            "Comparison disallowed between Queryable Encryption encrypted "
            "fields and non-constant expressions; field 'value' is encrypted."
        )
        with self.assertRaisesMessage(DatabaseError, msg):
            self.assertQuerySetEqual(
                model_cls.objects.filter(value__lte=F("value")), [low], attrgetter("value")
            )

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


class QueryTests(EncryptionTestCase):
    def test_aggregate_avg(self):
        msg = "Accumulator '$avg' cannot aggregate encrypted fields."
        with self.assertRaisesMessage(DatabaseError, msg):
            list(IntegerModel.objects.aggregate(Avg("value")))

    def test_aggregate_count(self):
        msg = "Invalid reference to an encrypted field within aggregate expression: value"
        with self.assertRaisesMessage(DatabaseError, msg):
            list(IntegerModel.objects.aggregate(Count("value")))

    def test_alias(self):
        msg = (
            "Cannot group on field '_id.value' which is encrypted with the "
            "random algorithm or whose encryption properties are not known "
            "until runtime"
        )
        with self.assertRaisesMessage(DatabaseError, msg):
            list(IntegerModel.objects.alias(avg=Avg("value")))

    def test_annotate(self):
        msg = (
            "Cannot group on field '_id.value' which is encrypted with the "
            "random algorithm or whose encryption properties are not known "
            "until runtime"
        )
        with self.assertRaisesMessage(DatabaseError, msg):
            list(IntegerModel.objects.annotate(avg=Avg("value")))

    def test_bulk_create(self):
        CharModel.objects.bulk_create([CharModel(value="abc"), CharModel(value="xyz")])
        self.assertQuerySetEqual(
            CharModel.objects.order_by("pk"), ["abc", "xyz"], attrgetter("value")
        )

    def test_bulk_update(self):
        objs = [
            CharModel.objects.create(value="abc"),
            CharModel.objects.create(value="xyz"),
        ]
        objs[0].value = "def"
        objs[1].value = "mno"
        msg = "Multi-document updates are not allowed with Queryable Encryption"
        with self.assertRaisesMessage(DatabaseError, msg):
            CharModel.objects.bulk_update(objs, ["value"])

    def test_contains(self):
        obj = CharModel.objects.create(value="abc")
        self.assertIs(CharModel.objects.contains(obj), True)

    def test_count(self):
        CharModel.objects.create(value="a")
        CharModel.objects.create(value="b")
        self.assertEqual(CharModel.objects.count(), 2)

    def test_dates(self):
        msg = (
            "If the value type is a date, the type of the index must also be date (and vice versa)."
        )
        with self.assertRaisesMessage(DatabaseError, msg):
            list(DateModel.objects.dates("value", "year"))

    def test_datetimes(self):
        msg = (
            "If the value type is a date, the type of the index must also be date (and vice versa)."
        )
        with self.assertRaisesMessage(DatabaseError, msg):
            list(DateTimeModel.objects.datetimes("value", "year"))

    def test_distinct(self):
        msg = (
            "Cannot group on field '_id.value' which is encrypted with the "
            "random algorithm or whose encryption properties are not known "
            "until runtime"
        )
        with self.assertRaisesMessage(DatabaseError, msg):
            list(CharModel.objects.distinct("value"))

    def test_exclude(self):
        obj1 = CharModel.objects.create(value="abc")
        obj2 = CharModel.objects.create(value="xyz")
        self.assertSequenceEqual(CharModel.objects.exclude(value=obj1.value), [obj2])

    def test_exists(self):
        self.assertIs(CharModel.objects.exists(), False)

    def test_get_or_create(self):
        obj1, created1 = CharModel.objects.get_or_create(value="abc")
        self.assertIs(created1, True)
        obj2, created2 = CharModel.objects.get_or_create(value="abc")
        self.assertIs(created2, False)
        self.assertEqual(obj1, obj2)

    def test_join(self):
        book = Book.objects.create(title="Book", author=Author.objects.create(name="Bob"))
        self.assertSequenceEqual(Book.objects.filter(author__name="Bob"), [book])

    def test_join_with_let(self):
        msg = (
            "Non-empty 'let' field is not allowed in the $lookup aggregation "
            "stage over an encrypted collection."
        )
        with self.assertRaisesMessage(DatabaseError, msg):
            list(Book.objects.filter(author__name=F("title")))

    def test_order_by(self):
        msg = "Cannot add an encrypted field as a prefix of another encrypted field"
        with self.assertRaisesMessage(DatabaseError, msg):
            list(CharModel.objects.order_by("value"))

    def test_select_related(self):
        Book.objects.create(title="Book", author=Author.objects.create(name="Bob"))
        with self.assertNumQueries(1, using="encrypted"):
            books = Book.objects.select_related("author")
            self.assertEqual(books[0].author.name, "Bob")

    def test_update(self):
        msg = "Multi-document updates are not allowed with Queryable Encryption"
        with self.assertRaisesMessage(DatabaseError, msg):
            self.assertEqual(CharModel.objects.update(value="xyz"), 1)

    def test_update_or_create(self):
        CharModel.objects.create(value="xyz")
        msg = "Multi-document updates are not allowed with Queryable Encryption"
        with self.assertRaisesMessage(DatabaseError, msg):
            CharModel.objects.update_or_create(value="xyz", defaults={"plain": "abc"})

    def test_union(self):
        msg = "Aggregation stage $unionWith is not allowed or supported with automatic encryption."
        qs1 = IntegerModel.objects.filter(value__gt=1)
        qs2 = IntegerModel.objects.filter(value__gte=8)
        with self.assertRaisesMessage(DatabaseError, msg):
            list(qs1.union(qs2))

    def test_values(self):
        list(CharModel.objects.values("value"))

    def test_values_list(self):
        list(CharModel.objects.values_list("value"))


class FieldMixinTests(EncryptionTestCase):
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
