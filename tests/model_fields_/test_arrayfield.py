import decimal
import enum
import json
import unittest
import uuid

from django.contrib.admin.utils import display_for_field
from django.core import checks, exceptions, serializers, validators
from django.core.exceptions import FieldError
from django.core.management import call_command
from django.db import IntegrityError, connection, models
from django.db.models.expressions import Exists, OuterRef, Value
from django.db.models.functions import Upper
from django.test import (
    SimpleTestCase,
    TestCase,
    TransactionTestCase,
    override_settings,
)
from django.test.utils import isolate_apps
from django.utils import timezone

from django_mongodb_backend.fields import ArrayField

from .models import (
    ArrayEnumModel,
    ArrayFieldSubclass,
    CharArrayModel,
    DateTimeArrayModel,
    IntegerArrayModel,
    NestedIntegerArrayModel,
    NullableIntegerArrayModel,
    OtherTypesArrayModel,
    Tag,
)


@isolate_apps("model_fields_")
class BasicTests(SimpleTestCase):
    def test_get_field_display(self):
        class MyModel(models.Model):
            field = ArrayField(
                models.CharField(max_length=16),
                choices=[
                    ["Media", [(["vinyl", "cd"], "Audio")]],
                    (("mp3", "mp4"), "Digital"),
                ],
            )

        tests = (
            (["vinyl", "cd"], "Audio"),
            (("mp3", "mp4"), "Digital"),
            (("a", "b"), "('a', 'b')"),
            (["c", "d"], "['c', 'd']"),
        )
        for value, display in tests:
            with self.subTest(value=value, display=display):
                instance = MyModel(field=value)
                self.assertEqual(instance.get_field_display(), display)

    def test_get_field_display_nested_array(self):
        class MyModel(models.Model):
            field = ArrayField(
                ArrayField(models.CharField(max_length=16)),
                choices=[
                    [
                        "Media",
                        [([["vinyl", "cd"], ("x",)], "Audio")],
                    ],
                    ((["mp3"], ("mp4",)), "Digital"),
                ],
            )

        tests = (
            ([["vinyl", "cd"], ("x",)], "Audio"),
            ((["mp3"], ("mp4",)), "Digital"),
            ((("a", "b"), ("c",)), "(('a', 'b'), ('c',))"),
            ([["a", "b"], ["c"]], "[['a', 'b'], ['c']]"),
        )
        for value, display in tests:
            with self.subTest(value=value, display=display):
                instance = MyModel(field=value)
                self.assertEqual(instance.get_field_display(), display)

    def test_deconstruct(self):
        field = ArrayField(models.IntegerField())
        name, path, args, kwargs = field.deconstruct()
        self.assertEqual(kwargs.keys(), {"base_field"})
        new = ArrayField(*args, **kwargs)
        self.assertEqual(type(new.base_field), type(field.base_field))
        self.assertIsNot(new.base_field, field.base_field)

    def test_deconstruct_with_max_size(self):
        field = ArrayField(models.IntegerField(), max_size=3)
        name, path, args, kwargs = field.deconstruct()
        new = ArrayField(*args, **kwargs)
        self.assertEqual(new.max_size, field.max_size)

    def test_deconstruct_args(self):
        field = ArrayField(models.CharField(max_length=20))
        name, path, args, kwargs = field.deconstruct()
        new = ArrayField(*args, **kwargs)
        self.assertEqual(new.base_field.max_length, field.base_field.max_length)

    def test_subclass_deconstruct(self):
        field = ArrayField(models.IntegerField())
        name, path, args, kwargs = field.deconstruct()
        self.assertEqual(path, "django_mongodb_backend.fields.ArrayField")

        field = ArrayFieldSubclass()
        name, path, args, kwargs = field.deconstruct()
        self.assertEqual(path, "model_fields_.models.ArrayFieldSubclass")


class SaveLoadTests(TestCase):
    def test_integer(self):
        instance = IntegerArrayModel(field=[1, 2, 3])
        instance.save()
        loaded = IntegerArrayModel.objects.get()
        self.assertEqual(instance.field, loaded.field)

    def test_char(self):
        instance = CharArrayModel(field=["hello", "goodbye"])
        instance.save()
        loaded = CharArrayModel.objects.get()
        self.assertEqual(instance.field, loaded.field)

    def test_dates(self):
        instance = DateTimeArrayModel(
            datetimes=[timezone.now().replace(microsecond=0)],
            dates=[timezone.now().date()],
            times=[timezone.now().time().replace(microsecond=0)],
        )
        instance.save()
        loaded = DateTimeArrayModel.objects.get()
        self.assertEqual(instance.datetimes, loaded.datetimes)
        self.assertEqual(instance.dates, loaded.dates)
        self.assertEqual(instance.times, loaded.times)

    def test_tuples(self):
        instance = IntegerArrayModel(field=(1,))
        instance.save()
        loaded = IntegerArrayModel.objects.get()
        self.assertSequenceEqual(instance.field, loaded.field)

    def test_integers_passed_as_strings(self):
        # This checks that get_prep_value() is deferred properly.
        instance = IntegerArrayModel(field=["1"])
        instance.save()
        loaded = IntegerArrayModel.objects.get()
        self.assertEqual(loaded.field, [1])

    def test_default_null(self):
        instance = NullableIntegerArrayModel()
        instance.save()
        loaded = NullableIntegerArrayModel.objects.get(pk=instance.pk)
        self.assertIsNone(loaded.field)
        self.assertEqual(instance.field, loaded.field)

    def test_null_handling(self):
        instance = NullableIntegerArrayModel(field=None)
        instance.save()
        loaded = NullableIntegerArrayModel.objects.get()
        self.assertEqual(instance.field, loaded.field)

    def test_save_null_in_non_null(self):
        instance = IntegerArrayModel(field=None)
        msg = "You can't set field (a non-nullable field) to None."
        with self.assertRaisesMessage(IntegrityError, msg):
            instance.save()

    def test_nested(self):
        instance = NestedIntegerArrayModel(field=[[1, 2], [3, 4]])
        instance.save()
        loaded = NestedIntegerArrayModel.objects.get()
        self.assertEqual(instance.field, loaded.field)

    def test_other_array_types(self):
        instance = OtherTypesArrayModel(
            ips=["192.168.0.1", "::1"],
            uuids=[uuid.uuid4()],
            decimals=[decimal.Decimal("1.25"), 1.75],
            tags=[Tag(1), Tag(2), Tag(3)],
            json=[{"a": 1}, {"b": 2}],
        )
        instance.save()
        loaded = OtherTypesArrayModel.objects.get()
        self.assertEqual(instance.ips, loaded.ips)
        self.assertEqual(instance.uuids, loaded.uuids)
        self.assertEqual(instance.decimals, loaded.decimals)
        self.assertEqual(instance.tags, loaded.tags)
        self.assertEqual(instance.json, loaded.json)

    def test_null_from_db_value_handling(self):
        instance = OtherTypesArrayModel.objects.create(
            ips=["192.168.0.1", "::1"],
            uuids=[uuid.uuid4()],
            decimals=None,
            tags=None,
        )
        instance.refresh_from_db()
        self.assertIsNone(instance.decimals)
        self.assertIsNone(instance.tags)
        self.assertEqual(instance.json, [])

    def test_model_set_on_base_field(self):
        instance = IntegerArrayModel()
        field = instance._meta.get_field("field")
        self.assertEqual(field.model, IntegerArrayModel)
        self.assertEqual(field.base_field.model, IntegerArrayModel)

    def test_nested_nullable_base_field(self):
        instance = NullableIntegerArrayModel.objects.create(
            field_nested=[[None, None], [None, None]],
        )
        self.assertEqual(instance.field_nested, [[None, None], [None, None]])


class QueryingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.objs = NullableIntegerArrayModel.objects.bulk_create(
            [
                NullableIntegerArrayModel(order=1, field=[1]),
                NullableIntegerArrayModel(order=2, field=[2]),
                NullableIntegerArrayModel(order=3, field=[2, 3]),
                NullableIntegerArrayModel(order=4, field=[20, 30, 40]),
                NullableIntegerArrayModel(order=5, field=None),
            ]
        )

    def test_empty_list(self):
        NullableIntegerArrayModel.objects.create(field=[])
        obj = (
            NullableIntegerArrayModel.objects.annotate(
                empty_array=models.Value([], output_field=ArrayField(models.IntegerField())),
            )
            .filter(field=models.F("empty_array"))
            .get()
        )
        self.assertEqual(obj.field, [])
        self.assertEqual(obj.empty_array, [])

    def test_exact(self):
        self.assertSequenceEqual(
            NullableIntegerArrayModel.objects.filter(field__exact=[1]), self.objs[:1]
        )

    def test_exact_null_only_array(self):
        obj = NullableIntegerArrayModel.objects.create(field=[None], field_nested=[None, None])
        self.assertSequenceEqual(
            NullableIntegerArrayModel.objects.filter(field__exact=[None]), [obj]
        )
        self.assertSequenceEqual(
            NullableIntegerArrayModel.objects.filter(field_nested__exact=[None, None]),
            [obj],
        )

    def test_exact_null_only_nested_array(self):
        obj1 = NullableIntegerArrayModel.objects.create(field_nested=[[None, None]])
        obj2 = NullableIntegerArrayModel.objects.create(
            field_nested=[[None, None], [None, None]],
        )
        self.assertSequenceEqual(
            NullableIntegerArrayModel.objects.filter(
                field_nested__exact=[[None, None]],
            ),
            [obj1],
        )
        self.assertSequenceEqual(
            NullableIntegerArrayModel.objects.filter(
                field_nested__exact=[[None, None], [None, None]],
            ),
            [obj2],
        )

    def test_exact_with_expression(self):
        self.assertSequenceEqual(
            NullableIntegerArrayModel.objects.filter(field__exact=[Value(1)]),
            self.objs[:1],
        )

    def test_exact_charfield(self):
        instance = CharArrayModel.objects.create(field=["text"])
        self.assertSequenceEqual(CharArrayModel.objects.filter(field=["text"]), [instance])

    def test_exact_nested(self):
        instance = NestedIntegerArrayModel.objects.create(field=[[1, 2], [3, 4]])
        self.assertSequenceEqual(
            NestedIntegerArrayModel.objects.filter(field=[[1, 2], [3, 4]]), [instance]
        )

    def test_isnull(self):
        self.assertSequenceEqual(
            NullableIntegerArrayModel.objects.filter(field__isnull=True), self.objs[-1:]
        )

    def test_gt(self):
        self.assertSequenceEqual(
            NullableIntegerArrayModel.objects.filter(field__gt=[0]), self.objs[:4]
        )

    def test_lt(self):
        self.assertSequenceEqual(
            NullableIntegerArrayModel.objects.filter(field__lt=[2]), self.objs[:1]
        )

    def test_in(self):
        self.assertSequenceEqual(
            NullableIntegerArrayModel.objects.filter(field__in=[[1], [2]]),
            self.objs[:2],
        )

    def test_in_subquery(self):
        IntegerArrayModel.objects.create(field=[2, 3])
        self.assertSequenceEqual(
            NullableIntegerArrayModel.objects.filter(
                field__in=IntegerArrayModel.objects.values_list("field", flat=True)
            ),
            self.objs[2:3],
        )

    @unittest.expectedFailure
    def test_in_including_F_object(self):
        # Array objects passed to filters can be constructed to contain
        # F objects. This doesn't work on PostgreSQL either (#27095).
        self.assertSequenceEqual(
            NullableIntegerArrayModel.objects.filter(field__in=[[models.F("id")]]),
            self.objs[:2],
        )

    def test_in_as_F_object(self):
        self.assertSequenceEqual(
            NullableIntegerArrayModel.objects.filter(field__in=[models.F("field")]),
            # Unlike PostgreSQL, MongoDB returns documents with field=null,
            # i.e. null is in [null]. It seems okay to leave this alone rather
            # than filtering out null in all $in queries. Feel free to
            # reconsider this decision if the behavior is problematic in some
            # other query.
            self.objs,
        )

    def test_contained_by(self):
        self.assertSequenceEqual(
            NullableIntegerArrayModel.objects.filter(field__contained_by=[1, 2]),
            self.objs[:2],
        )

    def test_contained_by_including_F_object(self):
        self.assertSequenceEqual(
            NullableIntegerArrayModel.objects.filter(field__contained_by=[models.F("order"), 2]),
            self.objs[:3],
        )

    def test_contains(self):
        self.assertSequenceEqual(
            NullableIntegerArrayModel.objects.filter(field__contains=[2]),
            self.objs[1:3],
        )

    def test_contains_subquery(self):
        IntegerArrayModel.objects.create(field=[2, 3])
        inner_qs = IntegerArrayModel.objects.values_list("field", flat=True)
        self.assertSequenceEqual(
            NullableIntegerArrayModel.objects.filter(field__contains=inner_qs[:1]),
            self.objs[2:3],
        )
        inner_qs = IntegerArrayModel.objects.filter(field__contains=OuterRef("field"))
        self.assertSequenceEqual(
            NullableIntegerArrayModel.objects.filter(Exists(inner_qs)),
            self.objs[1:3],
        )

    def test_contained_by_subquery(self):
        IntegerArrayModel.objects.create(field=[2, 3])
        inner_qs = IntegerArrayModel.objects.values_list("field", flat=True)
        self.assertSequenceEqual(
            NullableIntegerArrayModel.objects.filter(field__contained_by=inner_qs[:1]),
            self.objs[1:3],
        )
        IntegerArrayModel.objects.create(field=[2])
        inner_qs = IntegerArrayModel.objects.filter(field__contained_by=OuterRef("field"))
        self.assertSequenceEqual(
            NullableIntegerArrayModel.objects.filter(Exists(inner_qs)),
            self.objs[1:3],
        )

    def test_contains_including_expression(self):
        self.assertSequenceEqual(
            NullableIntegerArrayModel.objects.filter(
                field__contains=[2, Value(6) / Value(2)],
            ),
            self.objs[2:3],
        )

    def test_icontains(self):
        instance = CharArrayModel.objects.create(field=["FoO"])
        self.assertSequenceEqual(CharArrayModel.objects.filter(field__icontains="foo"), [instance])

    def test_contains_charfield(self):
        self.assertSequenceEqual(CharArrayModel.objects.filter(field__contains=["text"]), [])

    def test_contained_by_charfield(self):
        self.assertSequenceEqual(CharArrayModel.objects.filter(field__contained_by=["text"]), [])

    def test_overlap_charfield(self):
        self.assertSequenceEqual(CharArrayModel.objects.filter(field__overlap=["text"]), [])

    def test_overlap_charfield_including_expression(self):
        obj_1 = CharArrayModel.objects.create(field=["TEXT", "lower text"])
        obj_2 = CharArrayModel.objects.create(field=["lower text", "TEXT"])
        CharArrayModel.objects.create(field=["lower text", "text"])
        self.assertSequenceEqual(
            CharArrayModel.objects.filter(
                field__overlap=[
                    Upper(Value("text")),
                    "other",
                ]
            ),
            [obj_1, obj_2],
        )

    def test_overlap_values(self):
        qs = NullableIntegerArrayModel.objects.filter(order__lt=3)
        self.assertCountEqual(
            NullableIntegerArrayModel.objects.filter(
                field__overlap=qs.values_list("field"),
            ),
            self.objs[:3],
        )
        self.assertCountEqual(
            NullableIntegerArrayModel.objects.filter(
                field__overlap=qs.values("field"),
            ),
            self.objs[:3],
        )

    def test_index(self):
        self.assertSequenceEqual(
            NullableIntegerArrayModel.objects.filter(field__0=2), self.objs[1:3]
        )

    def test_index_chained(self):
        self.assertSequenceEqual(
            NullableIntegerArrayModel.objects.filter(field__0__lt=3), self.objs[0:3]
        )

    def test_index_nested(self):
        instance = NestedIntegerArrayModel.objects.create(field=[[1, 2], [3, 4]])
        self.assertSequenceEqual(NestedIntegerArrayModel.objects.filter(field__0__0=1), [instance])

    def test_index_used_on_nested_data(self):
        instance = NestedIntegerArrayModel.objects.create(field=[[1, 2], [3, 4]])
        self.assertSequenceEqual(
            NestedIntegerArrayModel.objects.filter(field__0=[1, 2]), [instance]
        )

    def test_overlap(self):
        self.assertSequenceEqual(
            NullableIntegerArrayModel.objects.filter(field__overlap=[1, 2]),
            self.objs[0:3],
        )

    def test_index_annotation(self):
        qs = NullableIntegerArrayModel.objects.annotate(second=models.F("field__1"))
        self.assertCountEqual(
            qs.values_list("second", flat=True),
            [None, None, None, 3, 30],
        )

    def test_len(self):
        self.assertSequenceEqual(
            NullableIntegerArrayModel.objects.filter(field__len__lte=2), self.objs[0:3]
        )

    def test_len_empty_array(self):
        obj = NullableIntegerArrayModel.objects.create(field=[])
        self.assertSequenceEqual(NullableIntegerArrayModel.objects.filter(field__len=0), [obj])

    def test_slice(self):
        self.assertSequenceEqual(
            NullableIntegerArrayModel.objects.filter(field__0_1=[2]), self.objs[1:3]
        )

        self.assertSequenceEqual(
            NullableIntegerArrayModel.objects.filter(field__0_2=[2, 3]), self.objs[2:3]
        )

    def test_order_by_index(self):
        more_objs = (
            NullableIntegerArrayModel.objects.create(field=[1, 637]),
            NullableIntegerArrayModel.objects.create(field=[2, 1]),
            NullableIntegerArrayModel.objects.create(field=[3, -98123]),
            NullableIntegerArrayModel.objects.create(field=[4, 2]),
        )
        self.assertSequenceEqual(
            NullableIntegerArrayModel.objects.order_by("field__1"),
            [
                self.objs[0],
                self.objs[1],
                self.objs[4],
                more_objs[2],
                more_objs[1],
                more_objs[3],
                self.objs[2],
                self.objs[3],
                more_objs[0],
            ],
        )

    def test_slice_nested(self):
        instance = NestedIntegerArrayModel.objects.create(field=[[1, 2], [3, 4]])
        self.assertSequenceEqual(
            NestedIntegerArrayModel.objects.filter(field__0__0_1=[1]), [instance]
        )

    def test_slice_annotation(self):
        qs = NullableIntegerArrayModel.objects.annotate(
            first_two=models.F("field__0_2"),
        )
        self.assertCountEqual(
            qs.values_list("first_two", flat=True),
            [None, [1], [2], [2, 3], [20, 30]],
        )

    def test_usage_in_subquery(self):
        self.assertSequenceEqual(
            NullableIntegerArrayModel.objects.filter(
                id__in=NullableIntegerArrayModel.objects.filter(field__len=3)
            ),
            [self.objs[3]],
        )

    def test_enum_lookup(self):
        class TestEnum(enum.Enum):
            VALUE_1 = "value_1"

        instance = ArrayEnumModel.objects.create(array_of_enums=[TestEnum.VALUE_1])
        self.assertSequenceEqual(
            ArrayEnumModel.objects.filter(array_of_enums__contains=[TestEnum.VALUE_1]),
            [instance],
        )

    def test_unsupported_lookup(self):
        msg = "Unsupported lookup '0_bar' for ArrayField or join on the field not permitted."
        with self.assertRaisesMessage(FieldError, msg):
            list(NullableIntegerArrayModel.objects.filter(field__0_bar=[2]))

        msg = "Unsupported lookup '0bar' for ArrayField or join on the field not permitted."
        with self.assertRaisesMessage(FieldError, msg):
            list(NullableIntegerArrayModel.objects.filter(field__0bar=[2]))


class DateTimeExactQueryingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        now = timezone.now()
        cls.datetimes = [now]
        cls.dates = [now.date()]
        cls.times = [now.time()]
        cls.objs = [
            DateTimeArrayModel.objects.create(
                datetimes=cls.datetimes, dates=cls.dates, times=cls.times
            ),
        ]

    def test_exact_datetimes(self):
        self.assertSequenceEqual(
            DateTimeArrayModel.objects.filter(datetimes=self.datetimes), self.objs
        )

    def test_exact_dates(self):
        self.assertSequenceEqual(DateTimeArrayModel.objects.filter(dates=self.dates), self.objs)

    def test_exact_times(self):
        self.assertSequenceEqual(DateTimeArrayModel.objects.filter(times=self.times), self.objs)


class OtherTypesExactQueryingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.ips = ["192.168.0.1", "::1"]
        cls.uuids = [uuid.uuid4()]
        cls.decimals = [decimal.Decimal("1.25"), 1.75]
        cls.tags = [Tag(1), Tag(2), Tag(3)]
        cls.objs = [
            OtherTypesArrayModel.objects.create(
                ips=cls.ips,
                uuids=cls.uuids,
                decimals=cls.decimals,
                tags=cls.tags,
            )
        ]

    def test_exact_ip_addresses(self):
        self.assertSequenceEqual(OtherTypesArrayModel.objects.filter(ips=self.ips), self.objs)

    def test_exact_uuids(self):
        self.assertSequenceEqual(OtherTypesArrayModel.objects.filter(uuids=self.uuids), self.objs)

    def test_exact_decimals(self):
        self.assertSequenceEqual(
            OtherTypesArrayModel.objects.filter(decimals=self.decimals), self.objs
        )

    def test_exact_tags(self):
        self.assertSequenceEqual(OtherTypesArrayModel.objects.filter(tags=self.tags), self.objs)


@isolate_apps("model_fields_")
class CheckTests(SimpleTestCase):
    def test_base_field_errors(self):
        class MyModel(models.Model):
            field = ArrayField(models.CharField(max_length=-1))

        model = MyModel()
        errors = model.check()
        self.assertEqual(len(errors), 1)
        # The inner CharField has a non-positive max_length.
        self.assertEqual(errors[0].id, "django_mongodb_backend.array.E001")
        msg = errors[0].msg
        self.assertIn("Base field for array has errors:", msg)
        self.assertIn("'max_length' must be a positive integer. (fields.E121)", msg)

    def test_base_field_warnings(self):
        class WarningField(models.IntegerField):
            def check(self):
                return [checks.Warning("Test warning", obj=self, id="test.E001")]

        class MyModel(models.Model):
            field = ArrayField(WarningField(), default=None)

        model = MyModel()
        errors = model.check()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].id, "django_mongodb_backend.array.W004")
        msg = errors[0].msg
        self.assertIn("Base field for array has warnings:", msg)
        self.assertIn("Test warning (test.E001)", msg)

    def test_invalid_base_fields(self):
        class MyModel(models.Model):
            field = ArrayField(models.ManyToManyField("model_fields_.IntegerArrayModel"))

        model = MyModel()
        errors = model.check()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].id, "django_mongodb_backend.array.E002")

    def test_both_size_and_max_size(self):
        class MyModel(models.Model):
            field = ArrayField(models.CharField(max_length=3), size=3, max_size=4)

        model = MyModel()
        errors = model.check()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].id, "django_mongodb_backend.array.E003")
        self.assertEqual(errors[0].msg, "ArrayField cannot have both size and max_size.")

    def test_invalid_default(self):
        class MyModel(models.Model):
            field = ArrayField(models.IntegerField(), default=[])

        model = MyModel()
        self.assertEqual(
            model.check(),
            [
                checks.Warning(
                    msg=(
                        "ArrayField default should be a callable instead of an "
                        "instance so that it's not shared between all field "
                        "instances."
                    ),
                    hint="Use a callable instead, e.g., use `list` instead of `[]`.",
                    obj=MyModel._meta.get_field("field"),
                    id="fields.E010",
                )
            ],
        )

    def test_valid_default(self):
        class MyModel(models.Model):
            field = ArrayField(models.IntegerField(), default=list)

        model = MyModel()
        self.assertEqual(model.check(), [])

    def test_valid_default_none(self):
        class MyModel(models.Model):
            field = ArrayField(models.IntegerField(), default=None)

        model = MyModel()
        self.assertEqual(model.check(), [])

    def test_nested_field_checks(self):
        """
        Nested ArrayFields are permitted.
        """

        class MyModel(models.Model):
            field = ArrayField(ArrayField(models.CharField(max_length=-1)))

        model = MyModel()
        errors = model.check()
        self.assertEqual(len(errors), 1)
        # The inner CharField has a non-positive max_length.
        self.assertEqual(errors[0].id, "django_mongodb_backend.array.E001")
        self.assertIn("max_length", errors[0].msg)

    def test_choices_tuple_list(self):
        class MyModel(models.Model):
            field = ArrayField(
                models.CharField(max_length=16),
                choices=[
                    [
                        "Media",
                        [(["vinyl", "cd"], "Audio"), (("vhs", "dvd"), "Video")],
                    ],
                    (["mp3", "mp4"], "Digital"),
                ],
            )

        self.assertEqual(MyModel._meta.get_field("field").check(), [])


@isolate_apps("model_fields_")
class MigrationsTests(TransactionTestCase):
    available_apps = ["model_fields_"]

    @override_settings(
        MIGRATION_MODULES={
            "model_fields_": "model_fields_.array_default_migrations",
        }
    )
    def test_adding_field_with_default(self):
        class IntegerArrayDefaultModel(models.Model):
            field = ArrayField(models.IntegerField())

        table_name = "model_fields__integerarraydefaultmodel"
        self.assertNotIn(table_name, connection.introspection.table_names(None))
        # Create collection
        call_command("migrate", "model_fields_", "0001", verbosity=0)
        self.assertIn(table_name, connection.introspection.table_names(None))
        obj = IntegerArrayDefaultModel.objects.create(field=[1, 2, 3])
        # Add `field2 to IntegerArrayDefaultModel.
        call_command("migrate", "model_fields_", "0002", verbosity=0)

        class UpdatedIntegerArrayDefaultModel(models.Model):
            field = ArrayField(models.IntegerField())
            field_2 = ArrayField(models.IntegerField(), default=[])

            class Meta:
                db_table = "model_fields__integerarraydefaultmodel"

        obj = UpdatedIntegerArrayDefaultModel.objects.get()
        # The default is populated on existing documents.
        self.assertEqual(obj.field_2, [])
        # Cleanup.
        call_command("migrate", "model_fields_", "zero", verbosity=0)
        self.assertNotIn(table_name, connection.introspection.table_names(None))

    @override_settings(
        MIGRATION_MODULES={
            "model_fields_": "model_fields_.array_index_migrations",
        }
    )
    def test_adding_arrayfield_with_index(self):
        table_name = "model_fields__chartextarrayindexmodel"
        call_command("migrate", "model_fields_", verbosity=0)
        # All fields should have indexes.
        indexes = [
            c["columns"][0]
            for c in connection.introspection.get_constraints(None, table_name).values()
            if c["index"] and len(c["columns"]) == 1
        ]
        self.assertIn("char", indexes)
        self.assertIn("char2", indexes)
        self.assertIn("text", indexes)
        call_command("migrate", "model_fields_", "zero", verbosity=0)
        self.assertNotIn(table_name, connection.introspection.table_names(None))


class SerializationTests(SimpleTestCase):
    test_data = (
        '[{"fields": {"field": "[\\"1\\", \\"2\\", null]"}, '
        '"model": "model_fields_.integerarraymodel", "pk": null}]'
    )

    def test_dumping(self):
        instance = IntegerArrayModel(field=[1, 2, None])
        data = serializers.serialize("json", [instance])
        self.assertEqual(json.loads(data), json.loads(self.test_data))

    def test_loading(self):
        instance = next(serializers.deserialize("json", self.test_data)).object
        self.assertEqual(instance.field, [1, 2, None])


class ValidationTests(SimpleTestCase):
    def test_unbounded(self):
        field = ArrayField(models.IntegerField())
        msg = "Item 2 in the array did not validate: This field cannot be null."
        with self.assertRaisesMessage(exceptions.ValidationError, msg) as cm:
            field.clean([1, None], None)
        self.assertEqual(cm.exception.code, "item_invalid")

    def test_blank_true(self):
        field = ArrayField(models.IntegerField(blank=True, null=True))
        # This should not raise a validation error
        field.clean([1, None], None)

    def test_with_max_size(self):
        field = ArrayField(models.IntegerField(), max_size=3)
        field.clean([1, 2, 3], None)
        msg = "List contains 4 items, it should contain no more than 3."
        with self.assertRaisesMessage(exceptions.ValidationError, msg):
            field.clean([1, 2, 3, 4], None)

    def test_with_max_size_singular(self):
        field = ArrayField(models.IntegerField(), max_size=1)
        field.clean([1], None)
        msg = "List contains 2 items, it should contain no more than 1."
        with self.assertRaisesMessage(exceptions.ValidationError, msg):
            field.clean([1, 2], None)

    def test_with_size(self):
        field = ArrayField(models.IntegerField(), size=3)
        field.clean([1, 2, 3], None)
        msg = "List contains 4 items, it should contain 3."
        with self.assertRaisesMessage(exceptions.ValidationError, msg):
            field.clean([1, 2, 3, 4], None)

    def test_with_size_singular(self):
        field = ArrayField(models.IntegerField(), size=2)
        field.clean([1, 2], None)
        msg = "List contains 1 item, it should contain 2."
        with self.assertRaisesMessage(exceptions.ValidationError, msg):
            field.clean([1], None)

    def test_nested_array_mismatch(self):
        field = ArrayField(ArrayField(models.IntegerField()))
        field.clean([[1, 2], [3, 4]], None)
        msg = "Nested arrays must have the same length."
        with self.assertRaisesMessage(exceptions.ValidationError, msg) as cm:
            field.clean([[1, 2], [3, 4, 5]], None)
        self.assertEqual(cm.exception.code, "nested_array_mismatch")

    def test_with_base_field_error_params(self):
        field = ArrayField(models.CharField(max_length=2))
        with self.assertRaises(exceptions.ValidationError) as cm:
            field.clean(["abc"], None)
        self.assertEqual(len(cm.exception.error_list), 1)
        exception = cm.exception.error_list[0]
        self.assertEqual(
            exception.message,
            "Item 1 in the array did not validate: Ensure this value has at most 2 "
            "characters (it has 3).",
        )
        self.assertEqual(exception.code, "item_invalid")
        self.assertEqual(
            exception.params,
            {"nth": 1, "value": "abc", "limit_value": 2, "show_value": 3},
        )

    def test_with_validators(self):
        field = ArrayField(models.IntegerField(validators=[validators.MinValueValidator(1)]))
        field.clean([1, 2], None)
        with self.assertRaises(exceptions.ValidationError) as cm:
            field.clean([0], None)
        self.assertEqual(len(cm.exception.error_list), 1)
        exception = cm.exception.error_list[0]
        self.assertEqual(
            exception.message,
            "Item 1 in the array did not validate: Ensure this value is greater than "
            "or equal to 1.",
        )
        self.assertEqual(exception.code, "item_invalid")
        self.assertEqual(
            exception.params, {"nth": 1, "value": 0, "limit_value": 1, "show_value": 0}
        )


class AdminUtilsTests(SimpleTestCase):
    empty_value = "-empty-"

    def test_array_display_for_field(self):
        array_field = ArrayField(models.IntegerField())
        display_value = display_for_field([1, 2], array_field, self.empty_value)
        self.assertEqual(display_value, "1, 2")

    def test_array_with_choices_display_for_field(self):
        array_field = ArrayField(
            models.IntegerField(),
            choices=[
                ([1, 2, 3], "1st choice"),
                ([1, 2], "2nd choice"),
            ],
        )
        display_value = display_for_field([1, 2], array_field, self.empty_value)
        self.assertEqual(display_value, "2nd choice")
        display_value = display_for_field([99, 99], array_field, self.empty_value)
        self.assertEqual(display_value, self.empty_value)
