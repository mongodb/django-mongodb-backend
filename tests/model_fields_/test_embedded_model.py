import operator
from datetime import timedelta

from django.core.exceptions import FieldDoesNotExist, ValidationError
from django.db import models
from django.db.models import (
    Exists,
    ExpressionWrapper,
    F,
    Max,
    OuterRef,
    Sum,
)
from django.test import SimpleTestCase, TestCase
from django.test.utils import isolate_apps

from django_mongodb_backend.fields import EmbeddedModelField
from django_mongodb_backend.models import EmbeddedModel

from .models import (
    Address,
    Author,
    Book,
    Data,
    Holder,
    Library,
    NestedData,
)
from .utils import truncate_ms


class MethodTests(SimpleTestCase):
    def test_deconstruct(self):
        field = EmbeddedModelField("Data", null=True)
        name, path, args, kwargs = field.deconstruct()
        self.assertEqual(path, "django_mongodb_backend.fields.EmbeddedModelField")
        self.assertEqual(args, [])
        self.assertEqual(kwargs, {"embedded_model": "Data", "null": True})

    def test_get_db_prep_save_invalid(self):
        msg = "Expected instance of type <class 'model_fields_.models.Data'>, not <class 'int'>."
        with self.assertRaisesMessage(TypeError, msg):
            Holder(data=42).save()

    def test_validate(self):
        obj = Holder(data=Data(integer=None))
        # This isn't quite right because "integer" is the subfield of data
        # that's non-null.
        msg = "{'data': ['This field cannot be null.']}"
        with self.assertRaisesMessage(ValidationError, msg):
            obj.full_clean()

    def test_validate_wrong_model_type(self):
        obj = Holder(data=Library())
        msg = (
            "{'data': [\"Expected instance of type "
            "<class 'model_fields_.models.Data'>, not "
            "<class 'model_fields_.models.Library'>.\"]}"
        )
        with self.assertRaisesMessage(ValidationError, msg):
            obj.full_clean()


class ModelTests(TestCase):
    def test_save_load(self):
        Holder.objects.create(data=Data(integer="5"))
        obj = Holder.objects.get()
        self.assertIsInstance(obj.data, Data)
        # get_prep_value() is called, transforming string to int.
        self.assertEqual(obj.data.integer, 5)
        # Primary keys should not be populated...
        self.assertEqual(obj.data.id, None)
        # ... unless set explicitly.
        obj.data.id = obj.id
        obj.save()
        obj = Holder.objects.get()
        self.assertEqual(obj.data.id, obj.id)

    def test_save_load_null(self):
        Holder.objects.create(data=None)
        obj = Holder.objects.get()
        self.assertIsNone(obj.data)

    def test_save_load_json(self):
        obj = Holder.objects.create(data=Data(json_value={"a": 1}))
        obj.refresh_from_db()
        self.assertEqual(obj.data.json_value, {"a": 1})

    def test_pre_save(self):
        """Field.pre_save() is called on embedded model fields."""
        obj = Holder.objects.create(data=Data())
        auto_now = truncate_ms(obj.data.auto_now)
        auto_now_add = truncate_ms(obj.data.auto_now_add)
        # auto_now and auto_now_add may differ by a millisecond since they
        # aren't generated simultaneously.
        self.assertAlmostEqual(auto_now, auto_now_add, delta=timedelta(microseconds=1000))
        # save() updates auto_now but not auto_now_add.
        obj.save()
        self.assertEqual(truncate_ms(obj.data.auto_now_add), auto_now_add)
        auto_now_two = obj.data.auto_now
        self.assertGreater(auto_now_two, obj.data.auto_now_add)
        # And again, save() updates auto_now but not auto_now_add.
        obj = Holder.objects.get()
        obj.save()
        self.assertEqual(obj.data.auto_now_add, auto_now_add)
        self.assertGreater(obj.data.auto_now, auto_now_two)


class QueryingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.objs = [
            Holder.objects.create(
                data=Data(
                    integer=x,
                    decimal=f"{x}.5",
                    nested_data=NestedData(decimal=f"{x}.5"),
                )
            )
            for x in range(6)
        ]

    def test_exact(self):
        self.assertCountEqual(Holder.objects.filter(data__integer=3), [self.objs[3]])

    def test_lt(self):
        self.assertCountEqual(Holder.objects.filter(data__integer__lt=3), self.objs[:3])

    def test_lte(self):
        self.assertCountEqual(Holder.objects.filter(data__integer__lte=3), self.objs[:4])

    def test_gt(self):
        self.assertCountEqual(Holder.objects.filter(data__integer__gt=3), self.objs[4:])

    def test_gte(self):
        self.assertCountEqual(Holder.objects.filter(data__integer__gte=3), self.objs[3:])

    def test_range(self):
        self.assertCountEqual(Holder.objects.filter(data__integer__range=(2, 4)), self.objs[2:5])

    def test_exact_decimal(self):
        # EmbeddedModelField lookups call
        # DatabaseOperations.adapt__<foo>field_value().
        self.assertCountEqual(Holder.objects.filter(data__decimal="3.5"), [self.objs[3]])

    def test_lt_decimal(self):
        self.assertCountEqual(Holder.objects.filter(data__decimal__lt="3"), self.objs[0:3])

    def test_exact_decimal_nested(self):
        self.assertCountEqual(
            Holder.objects.filter(data__nested_data__decimal="3.5"), [self.objs[3]]
        )

    def test_order_by_embedded_field(self):
        qs = Holder.objects.filter(data__integer__gt=3).order_by("-data__integer")
        self.assertSequenceEqual(qs, list(reversed(self.objs[4:])))

    def test_embedded_json_field_lookups(self):
        objs = [
            Holder.objects.create(
                data=Data(json_value={"field1": i * 5, "field2": {"0": {"value": list(range(i))}}})
            )
            for i in range(4)
        ]
        self.assertCountEqual(
            Holder.objects.filter(data__json_value__field2__0__value__0=0),
            objs[1:],
        )
        self.assertCountEqual(
            Holder.objects.filter(data__json_value__field2__0__value__1=1),
            objs[2:],
        )
        self.assertCountEqual(Holder.objects.filter(data__json_value__field2__0__value__1=5), [])
        self.assertCountEqual(Holder.objects.filter(data__json_value__field1__lt=100), objs)
        self.assertCountEqual(Holder.objects.filter(data__json_value__field1__gt=100), [])
        self.assertCountEqual(
            Holder.objects.filter(
                data__json_value__field1__gte=5, data__json_value__field1__lte=10
            ),
            objs[1:3],
        )

    def test_order_and_group_by_embedded_field(self):
        # Create and sort test data by `data__integer`.
        expected_objs = sorted(
            (Holder.objects.create(data=Data(integer=x)) for x in range(6)),
            key=lambda x: x.data.integer,
        )
        # Group by `data__integer + 5` and get the latest `data__auto_now`
        # datetime.
        qs = (
            Holder.objects.annotate(
                group=ExpressionWrapper(F("data__integer") + 5, output_field=models.IntegerField()),
            )
            .values("group")
            .annotate(max_auto_now=Max("data__auto_now"))
            .order_by("data__integer")
        )
        # Each unique `data__integer` is correctly grouped and annotated.
        self.assertSequenceEqual(
            [{**e, "max_auto_now": e["max_auto_now"]} for e in qs],
            [
                {"group": e.data.integer + 5, "max_auto_now": truncate_ms(e.data.auto_now)}
                for e in expected_objs
            ],
        )

    def test_order_and_group_by_embedded_field_annotation(self):
        # Create repeated `data__integer` values.
        [Holder.objects.create(data=Data(integer=x)) for x in range(6)]
        # Group by `data__integer` and compute the sum of occurrences.
        qs = (
            Holder.objects.values("data__integer")
            .annotate(sum=Sum("data__integer"))
            .order_by("sum")
        )
        # The sum is twice the integer values since each appears twice.
        self.assertQuerySetEqual(qs, [0, 2, 4, 6, 8, 10], operator.itemgetter("sum"))

    def test_nested(self):
        obj = Book.objects.create(
            author=Author(name="Shakespeare", age=55, address=Address(city="NYC", state="NY"))
        )
        self.assertCountEqual(Book.objects.filter(author__address__city="NYC"), [obj])


class ArrayFieldTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.book = Book.objects.create(
            author=Author(
                name="Shakespeare",
                age=55,
                skills=["writing", "editing"],
                address=Address(city="NYC", state="NY", tags=["home", "shipping"]),
            ),
        )

    def test_contains(self):
        self.assertCountEqual(Book.objects.filter(author__skills__contains=["nonexistent"]), [])
        self.assertCountEqual(
            Book.objects.filter(author__skills__contains=["writing"]), [self.book]
        )
        # Nested
        self.assertCountEqual(
            Book.objects.filter(author__address__tags__contains=["nonexistent"]), []
        )
        self.assertCountEqual(
            Book.objects.filter(author__address__tags__contains=["home"]), [self.book]
        )

    def test_contained_by(self):
        self.assertCountEqual(
            Book.objects.filter(author__skills__contained_by=["writing", "publishing"]), []
        )
        self.assertCountEqual(
            Book.objects.filter(author__skills__contained_by=["writing", "editing", "publishing"]),
            [self.book],
        )
        # Nested
        self.assertCountEqual(
            Book.objects.filter(author__address__tags__contained_by=["home", "work"]), []
        )
        self.assertCountEqual(
            Book.objects.filter(author__address__tags__contained_by=["home", "work", "shipping"]),
            [self.book],
        )

    def test_len(self):
        self.assertCountEqual(Book.objects.filter(author__skills__len=1), [])
        self.assertCountEqual(Book.objects.filter(author__skills__len=2), [self.book])
        # Nested
        self.assertCountEqual(Book.objects.filter(author__address__tags__len=1), [])
        self.assertCountEqual(Book.objects.filter(author__address__tags__len=2), [self.book])


class InvalidLookupTests(SimpleTestCase):
    def test_invalid_field(self):
        msg = "Author has no field named 'first_name'"
        with self.assertRaisesMessage(FieldDoesNotExist, msg):
            Book.objects.filter(author__first_name="Bob")

    def test_invalid_field_nested(self):
        msg = "Address has no field named 'floor'"
        with self.assertRaisesMessage(FieldDoesNotExist, msg):
            Book.objects.filter(author__address__floor="NYC")

    def test_invalid_lookup(self):
        msg = "Unsupported lookup 'foo' for CharField 'city'."
        with self.assertRaisesMessage(FieldDoesNotExist, msg):
            Book.objects.filter(author__address__city__foo="NYC")

    def test_invalid_lookup_with_suggestions(self):
        msg = (
            "Unsupported lookup '{lookup}' for CharField 'name', "
            "perhaps you meant {suggested_lookups}?"
        )
        with self.assertRaisesMessage(
            FieldDoesNotExist, msg.format(lookup="exactly", suggested_lookups="exact or iexact")
        ):
            Book.objects.filter(author__name__exactly="NYC")
        with self.assertRaisesMessage(
            FieldDoesNotExist, msg.format(lookup="gti", suggested_lookups="gt or gte")
        ):
            Book.objects.filter(author__name__gti="NYC")
        with self.assertRaisesMessage(
            FieldDoesNotExist, msg.format(lookup="is_null", suggested_lookups="isnull")
        ):
            Book.objects.filter(author__name__is_null="NYC")


@isolate_apps("model_fields_")
class CheckTests(SimpleTestCase):
    def test_no_relational_fields(self):
        class Target(EmbeddedModel):
            key = models.ForeignKey("MyModel", models.CASCADE)

        class MyModel(models.Model):
            field = EmbeddedModelField(Target)

        errors = MyModel().check()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].id, "django_mongodb_backend.embedded_model.E001")
        msg = errors[0].msg
        self.assertEqual(
            msg, "Embedded models cannot have relational fields (Target.key is a ForeignKey)."
        )

    def test_embedded_model_subclass(self):
        class Target(models.Model):
            pass

        class MyModel(models.Model):
            field = EmbeddedModelField(Target)

        errors = MyModel().check()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].id, "django_mongodb_backend.embedded_model.E002")
        msg = errors[0].msg
        self.assertEqual(
            msg,
            "Embedded models must be a subclass of django_mongodb_backend.models.EmbeddedModel.",
        )


class SubqueryExistsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        address1 = Address(city="New York", state="NY", zip_code=10001)
        address2 = Address(city="Boston", state="MA", zip_code=20002)
        author1 = Author(name="Alice", age=30, address=address1)
        author2 = Author(name="Bob", age=40, address=address2)
        book1 = Book.objects.create(name="Book 1", author=author1)
        book2 = Book.objects.create(name="Book 2", author=author2)
        Book.objects.create(name="Book 3", author=author2)
        Book.objects.create(name="Book 4", author=author2)
        Book.objects.create(name="Book 5", author=author1)
        library1 = Library.objects.create(name="Library 1", best_seller="Book 1")
        library2 = Library.objects.create(name="Library 2", best_seller="Book 1")
        library1.books.add(book1, book2)
        library2.books.add(book2)

    def test_exists_subquery(self):
        subquery = Book.objects.filter(
            author__name=OuterRef("author__name"), author__address__city="Boston"
        )
        qs = Book.objects.filter(Exists(subquery)).order_by("name")
        self.assertQuerySetEqual(qs, ["Book 2", "Book 3", "Book 4"], lambda book: book.name)

    def test_in_subquery(self):
        names = Book.objects.filter(author__age__gt=35).values("author__name")
        qs = Book.objects.filter(author__name__in=names).order_by("name")
        self.assertQuerySetEqual(qs, ["Book 2", "Book 3", "Book 4"], lambda book: book.name)

    def test_exists_with_foreign_object(self):
        subquery = Library.objects.filter(best_seller=OuterRef("name"))
        qs = Book.objects.filter(Exists(subquery))
        self.assertEqual(qs.first().name, "Book 1")

    def test_foreign_field_with_range(self):
        qs = Library.objects.filter(books__author__age__range=(25, 35))
        self.assertEqual(qs.first().name, "Library 1")
