from django.db import connection
from django.test import TestCase
from django.test.utils import isolate_apps

from django_mongodb_backend.constraints import EmbeddedFieldUniqueConstraint

from .models import DataHolder, Movie, Owner, Person, Store


@isolate_apps("constraints_")
class EmbeddedFieldUniqueConstraintTests(TestCase):
    def test_valid_embedded_model_subfield(self):
        constraint = EmbeddedFieldUniqueConstraint(
            name="constraint_name",
            fields=["data.integer"],
        )
        errors = constraint.check(DataHolder, connection=connection)
        self.assertEqual(errors, [])

    def test_nonexistent_embedded_model_subfield(self):
        constraint = EmbeddedFieldUniqueConstraint(
            name="constraint_name",
            fields=[
                "data.field_does_not_exist",
                "another_non_existing",
                "data.integer",
            ],
        )
        errors = constraint.check(DataHolder, connection=connection)
        self.assertEqual(len(errors), 2)
        self.assertEqual(errors[0].id, "models.E012")
        self.assertEqual(
            errors[0].msg,
            "'constraints' refers to the nonexistent field 'data.field_does_not_exist'.",
        )
        self.assertEqual(errors[1].id, "models.E012")
        self.assertEqual(
            errors[1].msg, "'constraints' refers to the nonexistent field 'another_non_existing'."
        )

    def test_valid_embedded_model_array_subfield(self):
        constraint = EmbeddedFieldUniqueConstraint(
            name="constraint_name",
            fields=["reviews.title"],
            nulls_distinct=False,
        )
        errors = constraint.check(Movie, connection=connection)
        self.assertEqual(errors, [])

    def test_nonexistent_embedded_model_array_subfield(self):
        constraint = EmbeddedFieldUniqueConstraint(
            name="constraint_name",
            fields=["reviews.author", "non_existing", "reviews.title"],
            nulls_distinct=False,
        )
        errors = constraint.check(Movie, connection=connection)
        self.assertEqual(len(errors), 2)
        self.assertEqual(errors[0].id, "models.E012")
        self.assertEqual(
            errors[0].msg,
            "'constraints' refers to the nonexistent field 'reviews.author'.",
        )
        self.assertEqual(errors[1].id, "models.E012")
        self.assertEqual(
            errors[1].msg, "'constraints' refers to the nonexistent field 'non_existing'."
        )

    def test_embedded_model_array_subfield_without_nulls_distinct(self):
        constraint = EmbeddedFieldUniqueConstraint(
            name="constraint_name",
            fields=["reviews.title"],
        )
        errors = constraint.check(Movie, connection=connection)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].id, "django_mongodb_backend.constraints.E001")
        self.assertEqual(
            errors[0].msg,
            "EmbeddedFieldUniqueConstraint 'constraint_name' must have "
            "nulls_distinct=False since it references EmbeddedModelArrayField "
            "'reviews'.",
        )

    def test_valid_polymorphic_embedded_model_subfield(self):
        constraint = EmbeddedFieldUniqueConstraint(
            name="constraint_name",
            fields=["pet.name"],
        )
        errors = constraint.check(Person, connection=connection)
        self.assertEqual(errors, [])

    def test_nonexistent_polymorphic_embedded_model_subfield(self):
        constraint = EmbeddedFieldUniqueConstraint(
            name="constraint_name",
            fields=["pet.nonexistent"],
        )
        errors = constraint.check(Person, connection=connection)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].id, "models.E012")
        self.assertEqual(
            errors[0].msg,
            "'constraints' refers to the nonexistent field 'pet.nonexistent'.",
        )

    def test_valid_polymorphic_embedded_model_array_subfield(self):
        constraint = EmbeddedFieldUniqueConstraint(
            name="constraint_name",
            fields=["pets.name"],
            nulls_distinct=False,
        )
        errors = constraint.check(Owner, connection=connection)
        self.assertEqual(errors, [])

    def test_nonexistent_polymorphic_embedded_model_array_subfield(self):
        constraint = EmbeddedFieldUniqueConstraint(
            name="constraint_name",
            fields=["pets.nonexistent"],
            nulls_distinct=False,
        )
        errors = constraint.check(Owner, connection=connection)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].id, "models.E012")
        self.assertEqual(
            errors[0].msg,
            "'constraints' refers to the nonexistent field 'pets.nonexistent'.",
        )

    def test_polymorphic_embedded_model_array_subfield_without_nulls_distinct(self):
        constraint = EmbeddedFieldUniqueConstraint(
            name="constraint_name",
            fields=["pets.name"],
        )
        errors = constraint.check(Owner, connection=connection)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].id, "django_mongodb_backend.constraints.E001")
        self.assertEqual(
            errors[0].msg,
            "EmbeddedFieldUniqueConstraint 'constraint_name' must have "
            "nulls_distinct=False since it references PolymorphicEmbeddedModelArrayField "
            "'pets'.",
        )

    def test_valid_nested_polymorphic_subfield(self):
        constraint = EmbeddedFieldUniqueConstraint(name="name", fields=["thing.tags.name"])
        errors = constraint.check(Store, connection=connection)
        self.assertEqual(errors, [])

    def test_nonexistent_nested_polymorphic_subfield(self):
        constraint = EmbeddedFieldUniqueConstraint(name="name", fields=["thing.tags.xxx"])
        errors = constraint.check(Store, connection=connection)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].id, "models.E012")
        self.assertEqual(
            errors[0].msg,
            "'constraints' refers to the nonexistent field 'thing.tags.xxx'.",
        )
