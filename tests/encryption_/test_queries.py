from operator import attrgetter

from django.db import DatabaseError
from django.db.models import Avg, Count, F

from .models import Author, Book, CharModel, DateModel, DateTimeModel, IntegerModel
from .test_base import EncryptionTestCase


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
