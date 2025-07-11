from decimal import Decimal

from django.core.exceptions import FieldDoesNotExist
from django.db import models
from django.test import SimpleTestCase, TestCase
from django.test.utils import isolate_apps

from django_mongodb_backend.fields import PolymorphicEmbeddedModelArrayField
from django_mongodb_backend.models import EmbeddedModel

from .models import Bone, Cat, Dog, Owner


class MethodTests(SimpleTestCase):
    def test_not_editable(self):
        field = PolymorphicEmbeddedModelArrayField(["Dog"])
        self.assertIs(field.editable, False)

    def test_deconstruct(self):
        field = PolymorphicEmbeddedModelArrayField(["Dog"], null=True)
        name, path, args, kwargs = field.deconstruct()
        self.assertEqual(path, "django_mongodb_backend.fields.PolymorphicEmbeddedModelArrayField")
        self.assertEqual(args, [])
        self.assertEqual(kwargs, {"embedded_models": ["Dog"], "null": True})

    def test_size_not_supported(self):
        msg = "PolymorphicEmbeddedModelArrayField does not support size."
        with self.assertRaisesMessage(ValueError, msg):
            PolymorphicEmbeddedModelArrayField("Data", size=1)

    def test_get_db_prep_save_invalid(self):
        msg = (
            "Expected list of (<class 'model_fields_.models.Dog'>, "
            "<class 'model_fields_.models.Cat'>) instances, not <class 'int'>."
        )
        with self.assertRaisesMessage(TypeError, msg):
            Owner(pets=42).save()

    def test_get_db_prep_save_invalid_list(self):
        msg = (
            "Expected instance of type (<class 'model_fields_.models.Dog'>, "
            "<class 'model_fields_.models.Cat'>), not <class 'int'>."
        )
        with self.assertRaisesMessage(TypeError, msg):
            Owner(pets=[42]).save()


class ModelTests(TestCase):
    def test_save_load(self):
        pets = [Dog(name="Woofer"), Cat(name="Phoebe", weight="3.5")]
        Owner.objects.create(name="Bob", pets=pets)
        owner = Owner.objects.get(name="Bob")
        self.assertEqual(owner.pets[0].name, "Woofer")
        self.assertEqual(owner.pets[1].name, "Phoebe")
        self.assertEqual(owner.pets[1].weight, Decimal("3.5"))
        self.assertEqual(len(owner.pets), 2)

    def test_save_load_null(self):
        Owner.objects.create(name="Bob")
        owner = Owner.objects.get(name="Bob")
        self.assertIsNone(owner.pets)


class QueryingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.fred = Owner.objects.create(
            name="Fred",
            pets=[
                Dog(name="Woofer", toys=[Bone(brand="Brand 1")]),
                Cat(name="Phoebe", weight="3.5"),
            ],
        )
        cls.bob = Owner.objects.create(
            name="Bob",
            pets=[Dog(name="Lassy", toys=[Bone(brand="Brand 1")])],
        )
        cls.mary = Owner.objects.create(
            name="Mary",
            pets=[
                Dog(name="Doodle"),
                Cat(name="Tyler"),
            ],
        )
        cls.julie = Owner.objects.create(
            name="Mary",
            pets=[
                Cat(name="General"),
                Dog(name="Skip", toys=[Bone(brand="Brand 2")]),
            ],
        )

    def test_exact(self):
        self.assertCountEqual(Owner.objects.filter(pets__name="Woofer"), [self.fred])

    def test_array_index(self):
        self.assertCountEqual(Owner.objects.filter(pets__0__name="Lassy"), [self.bob])

    def test_nested_array_index(self):
        self.assertCountEqual(
            Owner.objects.filter(pets__toys__0__brand="Brand 1"), [self.fred, self.bob]
        )

    def test_array_slice(self):
        self.assertSequenceEqual(Owner.objects.filter(pets__0_1__name="Woofer"), [self.fred])

    #    def test_filter_unsupported_lookups_in_json(self):
    #        """Unsupported lookups can be used as keys in a JSONField."""
    #        for lookup in ["contains", "range"]:
    #            kwargs = {f"main_sectionigin__{lookup}": ["Pergamon", "Egypt"]}
    #            with CaptureQueriesContext(connection) as captured_queries:
    #                self.assertCountEqual(Exhibit.objects.filter(**kwargs), [])
    #                self.assertIn(f"'field': '{lookup}'", captured_queries[0]["sql"])

    def test_len(self):
        self.assertCountEqual(Owner.objects.filter(pets__len=3), [])
        self.assertCountEqual(
            Owner.objects.filter(pets__len=2),
            [self.fred, self.mary, self.julie],
        )
        # Nested EMF
        self.assertCountEqual(
            Owner.objects.filter(pets__toys__len=1), [self.fred, self.bob, self.julie]
        )
        self.assertCountEqual(Owner.objects.filter(pets__toys__len=2), [])
        # Nested Indexed Array
        self.assertCountEqual(Owner.objects.filter(pets__0__toys__len=1), [self.fred, self.bob])
        self.assertCountEqual(Owner.objects.filter(pets__0__toys__len=0), [])
        self.assertCountEqual(Owner.objects.filter(pets__1__toys__len=1), [self.julie])

    def test_in(self):
        self.assertCountEqual(Owner.objects.filter(pets__weight__in=["4.0"]), [])
        self.assertCountEqual(Owner.objects.filter(pets__weight__in=["3.5"]), [self.fred])

    def test_iexact(self):
        self.assertCountEqual(Owner.objects.filter(pets__name__iexact="woofer"), [self.fred])

    def test_gt(self):
        self.assertCountEqual(Owner.objects.filter(pets__weight__gt=1), [self.fred])

    def test_gte(self):
        self.assertCountEqual(Owner.objects.filter(pets__weight__gte=1), [self.fred])

    def test_lt(self):
        self.assertCountEqual(Owner.objects.filter(pets__weight__lt=2), [])

    def test_lte(self):
        self.assertCountEqual(Owner.objects.filter(pets__weight__lte=2), [])

    def test_querying_array_not_allowed(self):
        msg = (
            "Lookups aren't supported on PolymorphicEmbeddedModelArrayField. "
            "Try querying one of its embedded fields instead."
        )
        with self.assertRaisesMessage(ValueError, msg):
            Owner.objects.filter(pets=10).first()

        with self.assertRaisesMessage(ValueError, msg):
            Owner.objects.filter(pets__0_1=10).first()

    def test_invalid_field(self):
        msg = "The models of field 'pets' have no field named 'xxx'."
        with self.assertRaisesMessage(FieldDoesNotExist, msg):
            Owner.objects.filter(pets__xxx=10).first()

    def test_invalid_lookup(self):
        msg = "Unsupported lookup 'return' for PolymorphicEmbeddedModelArrayField " "of 'CharField'"
        with self.assertRaisesMessage(FieldDoesNotExist, msg):
            Owner.objects.filter(pets__name__return="xxx")

    def test_unsupported_lookup(self):
        msg = (
            "Unsupported lookup 'range' for PolymorphicEmbeddedModelArrayField " "of 'DecimalField'"
        )
        with self.assertRaisesMessage(FieldDoesNotExist, msg):
            Owner.objects.filter(pets__weight__range=[10])

    def test_missing_lookup_suggestions(self):
        msg = (
            "Unsupported lookup 'ltee' for PolymorphicEmbeddedModelArrayField "
            "of 'DecimalField', perhaps you meant lte or lt?"
        )
        with self.assertRaisesMessage(FieldDoesNotExist, msg):
            Owner.objects.filter(pets__weight__ltee=3)

    def test_nested_lookup(self):
        msg = "Cannot perform multiple levels of array traversal in a query."
        with self.assertRaisesMessage(ValueError, msg):
            Owner.objects.filter(pets__toys__name="")


#    def test_foreign_field_exact(self):
#        """Querying from a foreign key to an PolymorphicEmbeddedModelArrayField."""
#        qs = Tour.objects.filter(exhibit__sections__number=1)
#        self.assertCountEqual(qs, [self.egypt_tour, self.wonders_tour])

#    def test_foreign_field_with_slice(self):
#        qs = Tour.objects.filter(exhibit__sections__0_2__number__in=[1, 2])
#        self.assertCountEqual(qs, [self.wonders_tour, self.egypt_tour])

#    def test_subquery_numeric_lookups(self):
#        subquery = Audit.objects.filter(
#            section_number__in=models.OuterRef("sections__number")
#        ).values("section_number")[:1]
#        tests = [
#            ("exact", [self.egypt, self.new_descoveries, self.wonders]),
#            ("lt", []),
#            ("lte", [self.egypt, self.new_descoveries, self.wonders]),
#            ("gt", [self.wonders]),
#            ("gte", [self.egypt, self.new_descoveries, self.wonders]),
#        ]
#        for lookup, expected in tests:
#            with self.subTest(lookup=lookup):
#                kwargs = {f"sections__number__{lookup}": subquery}
#                self.assertCountEqual(Exhibit.objects.filter(**kwargs), expected)

#    def test_subquery_in_lookup(self):
#        subquery = Audit.objects.filter(reviewed=True).values_list("section_number", flat=True)
#        result = Exhibit.objects.filter(sections__number__in=subquery)
#        self.assertCountEqual(result, [self.wonders, self.new_descoveries, self.egypt])

#    def test_array_as_rhs(self):
#        result = Exhibit.objects.filter(main_section__number__in=models.F("sections__number"))
#        self.assertCountEqual(result, [self.new_descoveries])

#    def test_array_annotation_lookup(self):
#        result = Exhibit.objects.annotate(section_numbers=models.F("main_section__number")).filter(
#            section_numbers__in=models.F("sections__number")
#        )
#        self.assertCountEqual(result, [self.new_descoveries])

#    def test_array_as_rhs_for_arrayfield_lookups(self):
#        tests = [
#            ("exact", [self.wonders]),
#            ("lt", [self.new_descoveries]),
#            ("lte", [self.wonders, self.new_descoveries]),
#            ("gt", [self.egypt, self.lost_empires]),
#            ("gte", [self.egypt, self.wonders, self.lost_empires]),
#            ("overlap", [self.egypt, self.wonders, self.new_descoveries]),
#            ("contained_by", [self.wonders]),
#            ("contains", [self.egypt, self.wonders, self.new_descoveries, self.lost_empires]),
#        ]
#        for lookup, expected in tests:
#            with self.subTest(lookup=lookup):
#                kwargs = {f"section_numbers__{lookup}": models.F("sections__number")}
#                result = Exhibit.objects.annotate(
#                    section_numbers=Value(
#                        [1, 2], output_field=ArrayField(base_field=models.IntegerField())
#                    )
#                ).filter(**kwargs)
#                self.assertCountEqual(result, expected)

#    def test_array_annotation(self):
#        qs = Exhibit.objects.annotate(section_numbers=models.F("sections__nber")).order_by("name")
#        self.assertQuerySetEqual(qs, [[1], [], [2], [1, 2]], attrgetter("section_numbers"))


@isolate_apps("model_fields_")
class CheckTests(SimpleTestCase):
    def test_no_relational_fields(self):
        class Target(EmbeddedModel):
            key = models.ForeignKey("MyModel", models.CASCADE)

        class MyModel(models.Model):
            field = PolymorphicEmbeddedModelArrayField([Target])

        errors = MyModel().check()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].id, "django_mongodb_backend.array.E001")
        msg = errors[0].msg
        self.assertEqual(
            msg,
            "Base field for array has errors:\n    "
            "Embedded models cannot have relational fields (Target.key is a ForeignKey). "
            "(django_mongodb_backend.embedded_model.E001)",
        )

    def test_embedded_model_subclass(self):
        class Target(models.Model):
            pass

        class MyModel(models.Model):
            field = PolymorphicEmbeddedModelArrayField([Target])

        errors = MyModel().check()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].id, "django_mongodb_backend.array.E001")
        msg = errors[0].msg
        self.assertEqual(
            msg,
            "Base field for array has errors:\n    "
            "Embedded models must be a subclass of "
            "django_mongodb_backend.models.EmbeddedModel. "
            "(django_mongodb_backend.embedded_model.E002)",
        )

    def test_clashing_fields(self):
        class Target1(EmbeddedModel):
            clash = models.DecimalField(max_digits=4, decimal_places=2)

        class Target2(EmbeddedModel):
            clash = models.CharField(max_length=255)

        class MyModel(models.Model):
            field = PolymorphicEmbeddedModelArrayField([Target1, Target2])

        errors = MyModel().check()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].id, "django_mongodb_backend.array.W004")
        self.assertEqual(
            errors[0].msg,
            "Base field for array has warnings:\n    "
            "Embedded models model_fields_.Target1 and model_fields_.Target2 "
            "both have field 'clash' of different type. "
            "(django_mongodb_backend.embedded_model.E003)",
        )

    def test_clashing_fields_of_same_type(self):
        """Fields of different type don't clash if they use the same db_type."""

        class Target1(EmbeddedModel):
            clash = models.TextField()

        class Target2(EmbeddedModel):
            clash = models.CharField(max_length=255)

        class MyModel(models.Model):
            field = PolymorphicEmbeddedModelArrayField([Target1, Target2])

        errors = MyModel().check()
        self.assertEqual(len(errors), 0)
