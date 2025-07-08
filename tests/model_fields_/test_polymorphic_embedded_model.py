from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import FieldDoesNotExist, ValidationError
from django.db import models
from django.test import SimpleTestCase, TestCase
from django.test.utils import isolate_apps

from django_mongodb_backend.fields import PolymorphicEmbeddedModelField
from django_mongodb_backend.models import EmbeddedModel

from .models import Bone, Cat, Dog, Library, Mouse, Person
from .utils import truncate_ms


class MethodTests(SimpleTestCase):
    def test_not_editable(self):
        field = PolymorphicEmbeddedModelField(["Data"], null=True)
        self.assertIs(field.editable, False)

    def test_deconstruct(self):
        field = PolymorphicEmbeddedModelField(["Data"], null=True)
        name, path, args, kwargs = field.deconstruct()
        self.assertEqual(path, "django_mongodb_backend.fields.PolymorphicEmbeddedModelField")
        self.assertEqual(args, [])
        self.assertEqual(kwargs, {"embedded_models": ["Data"], "null": True})

    def test_get_db_prep_save_invalid(self):
        msg = (
            "Expected instance of type (<class 'model_fields_.models.Dog'>, "
            "<class 'model_fields_.models.Cat'>), "
            "not <class 'int'>."
        )
        with self.assertRaisesMessage(TypeError, msg):
            Person(pet=42).save()

    def test_validate(self):
        obj = Person(name="Bob", pet=Dog(name="Woofer", barks=None))
        # This isn't quite right because "barks" is the subfield of data
        # that's non-null.
        msg = "{'pet': ['This field cannot be null.']}"
        with self.assertRaisesMessage(ValidationError, msg):
            obj.full_clean()

    def test_validate_wrong_model_type(self):
        obj = Person(name="Bob", pet=Library())
        msg = (
            "{'pet': [\"Expected instance of type "
            "(<class 'model_fields_.models.Dog'>, "
            "<class 'model_fields_.models.Cat'>), not "
            "<class 'model_fields_.models.Library'>.\"]}"
        )
        with self.assertRaisesMessage(ValidationError, msg):
            obj.full_clean()


class ModelTests(TestCase):
    def test_save_load(self):
        Person.objects.create(name="Jim", pet=Dog(name="Woofer"))
        obj = Person.objects.get()
        self.assertIsInstance(obj.pet, Dog)
        # get_prep_value() is called, transforming string to int.
        self.assertEqual(obj.pet.name, "Woofer")
        # Primary keys should not be populated...
        self.assertEqual(obj.pet.id, None)
        # ... unless set explicitly.
        obj.pet.id = obj.id
        obj.save()
        obj = Person.objects.get()
        self.assertEqual(obj.pet.id, obj.id)

    def test_save_load_null(self):
        Person.objects.create(pet=None)
        obj = Person.objects.get()
        self.assertIsNone(obj.pet)

    def test_save_load_decimal(self):
        obj = Person.objects.create(pet=Cat(name="Phoebe", weight="5.5"))
        obj.refresh_from_db()
        self.assertEqual(obj.pet.weight, Decimal("5.5"))

    def test_pre_save(self):
        """Field.pre_save() is called on embedded model fields."""
        obj = Person.objects.create(name="Bob", pet=Dog(name="Woofer"))
        created_at = truncate_ms(obj.pet.created_at)
        updated_at = truncate_ms(obj.pet.updated_at)
        self.assertIsNotNone(obj.pet.created_at)
        # The values may differ by a millisecond since they aren't generated
        # simultaneously.
        self.assertAlmostEqual(updated_at, created_at, delta=timedelta(microseconds=1000))


class QueryingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.cat_owners = [
            Person.objects.create(
                name=f"Cat Owner {x}",
                pet=Cat(
                    name=f"Cat {x}",
                    weight=f"{x}.5",
                    favorite_toy=Mouse(manufacturer=f"Maker {x}"),
                ),
            )
            for x in range(6)
        ]
        cls.dog_owners = [
            Person.objects.create(
                name=f"Dog Owner {x}",
                pet=Dog(
                    name=f"Dog {x}",
                    barks=x % 2 == 0,
                    favorite_toy=Bone(brand=f"Brand {x}"),
                ),
            )
            for x in range(6)
        ]

    def test_exact(self):
        self.assertCountEqual(Person.objects.filter(pet__weight="3.5"), [self.cat_owners[3]])

    def test_lt(self):
        self.assertCountEqual(Person.objects.filter(pet__weight__lt="3.5"), self.cat_owners[:3])

    def test_lte(self):
        self.assertCountEqual(Person.objects.filter(pet__weight__lte="3.5"), self.cat_owners[:4])

    def test_gt(self):
        self.assertCountEqual(Person.objects.filter(pet__weight__gt=3.5), self.cat_owners[4:])

    def test_gte(self):
        self.assertCountEqual(Person.objects.filter(pet__weight__gte=3.5), self.cat_owners[3:])

    def test_range(self):
        self.assertCountEqual(
            Person.objects.filter(pet__weight__range=(2, 4)), self.cat_owners[2:4]
        )

    def test_order_by_embedded_field(self):
        qs = Person.objects.filter(pet__weight__gt=3).order_by("-pet__weight")
        self.assertSequenceEqual(qs, list(reversed(self.cat_owners[3:])))

    def test_boolean(self):
        self.assertCountEqual(
            Person.objects.filter(pet__barks=True),
            [x for i, x in enumerate(self.dog_owners) if i % 2 == 0],
        )

    def test_nested(self):
        # Cat and Dog both have favorite_toy = PolymorphicEmbeddedModelField(...)
        # but with different models. It's possible to query the fields of the
        # Dog's favorite_toy because it's the first model in Person.pet.
        self.assertCountEqual(
            Person.objects.filter(pet__favorite_toy__brand="Brand 1"),
            [self.dog_owners[1]],
        )
        # The fields of Cat can't be queried.
        msg = "The models of field 'favorite_toy' have no field named 'manufacturer'."
        with self.assertRaisesMessage(FieldDoesNotExist, msg):
            (Person.objects.filter(pet__favorite_toy__manufacturer="Maker 1"),)


class InvalidLookupTests(SimpleTestCase):
    def test_invalid_field(self):
        msg = "The models of field 'pet' have no field named 'first_name'."
        with self.assertRaisesMessage(FieldDoesNotExist, msg):
            Person.objects.filter(pet__first_name="Bob")

    def test_invalid_lookup(self):
        msg = "Unsupported lookup 'foo' for CharField 'name'."
        with self.assertRaisesMessage(FieldDoesNotExist, msg):
            Person.objects.filter(pet__name__foo="Bob")

    def test_invalid_lookup_with_suggestions(self):
        msg = (
            "Unsupported lookup '{lookup}' for CharField 'name', "
            "perhaps you meant {suggested_lookups}?"
        )
        with self.assertRaisesMessage(
            FieldDoesNotExist, msg.format(lookup="exactly", suggested_lookups="exact or iexact")
        ):
            Person.objects.filter(pet__name__exactly="Woof")
        with self.assertRaisesMessage(
            FieldDoesNotExist, msg.format(lookup="gti", suggested_lookups="gt or gte")
        ):
            Person.objects.filter(pet__name__gti="Woof")
        with self.assertRaisesMessage(
            FieldDoesNotExist, msg.format(lookup="is_null", suggested_lookups="isnull")
        ):
            Person.objects.filter(pet__name__is_null="Woof")


@isolate_apps("model_fields_")
class CheckTests(SimpleTestCase):
    def test_no_relational_fields(self):
        class Target(EmbeddedModel):
            key = models.ForeignKey("MyModel", models.CASCADE)

        class MyModel(models.Model):
            field = PolymorphicEmbeddedModelField([Target])

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
            field = PolymorphicEmbeddedModelField([Target])

        errors = MyModel().check()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].id, "django_mongodb_backend.embedded_model.E002")
        msg = errors[0].msg
        self.assertEqual(
            msg,
            "Embedded models must be a subclass of django_mongodb_backend.models.EmbeddedModel.",
        )

    def test_clashing_fields(self):
        class Target1(EmbeddedModel):
            clash = models.DecimalField(max_digits=4, decimal_places=2)

        class Target2(EmbeddedModel):
            clash = models.CharField(max_length=255)

        class MyModel(models.Model):
            field = PolymorphicEmbeddedModelField([Target1, Target2])

        errors = MyModel().check()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].id, "django_mongodb_backend.embedded_model.E003")
        self.assertEqual(
            errors[0].msg,
            "Embedded models model_fields_.Target1 and model_fields_.Target2 "
            "both have field 'clash' of different type.",
        )
        self.assertEqual(
            errors[0].hint,
            "It may be impossible to query both fields.",
        )

    def test_clashing_fields_of_same_type(self):
        """Fields of different type don't clash if they use the same db_type."""

        class Target1(EmbeddedModel):
            clash = models.TextField()

        class Target2(EmbeddedModel):
            clash = models.CharField(max_length=255)

        class MyModel(models.Model):
            field = PolymorphicEmbeddedModelField([Target1, Target2])

        errors = MyModel().check()
        self.assertEqual(len(errors), 0)
