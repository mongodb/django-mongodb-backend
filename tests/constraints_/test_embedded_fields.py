from django.core.exceptions import FieldDoesNotExist
from django.db import IntegrityError, connection
from django.test import TestCase

from django_mongodb_backend.constraints import EmbeddedFieldUniqueConstraint

from .models import Data, DataHolder, Movie, Review


class EmbeddedFieldUniqueConstraintTests(TestCase):
    def test_embedded_model_subfield(self):
        constraint = EmbeddedFieldUniqueConstraint(
            name="embedded_created_constraint",
            fields=["data.integer"],
        )
        with connection.schema_editor() as editor:
            editor.add_constraint(constraint=constraint, model=DataHolder)
        try:
            constraint_info = connection.introspection.get_constraints(
                cursor=None,
                table_name=DataHolder._meta.db_table,
            )
            self.assertIn(constraint.name, constraint_info)
            self.assertCountEqual(
                constraint_info[constraint.name]["columns"],
                constraint.fields,
            )
            self.assertEqual(constraint_info[constraint.name]["type"], "idx")
            DataHolder.objects.create(data=Data(integer=1))
            msg = "embedded_created_constraint dup key: { data.integer: 1 }"
            with self.assertRaisesMessage(IntegrityError, msg):
                DataHolder.objects.create(data=Data(integer=1))
        finally:
            with connection.schema_editor() as editor:
                editor.remove_constraint(constraint=constraint, model=DataHolder)

    def test_multiple_fields(self):
        constraint = EmbeddedFieldUniqueConstraint(
            name="embedded_multi_constraint",
            fields=["integer", "data.integer"],
        )
        with connection.schema_editor() as editor:
            editor.add_constraint(constraint=constraint, model=DataHolder)
        try:
            constraint_info = connection.introspection.get_constraints(
                cursor=None,
                table_name=DataHolder._meta.db_table,
            )
            self.assertIn(constraint.name, constraint_info)
            self.assertCountEqual(
                constraint_info[constraint.name]["columns"],
                constraint.fields,
            )
        finally:
            with connection.schema_editor() as editor:
                editor.remove_constraint(constraint=constraint, model=DataHolder)

    def test_embedded_model_array_subfield(self):
        constraint = EmbeddedFieldUniqueConstraint(
            name="embedded_multi_idx",
            fields=["reviews.rating"],
            nulls_distinct=False,
        )
        with connection.schema_editor() as editor:
            editor.add_constraint(constraint=constraint, model=Movie)
        try:
            constraint_info = connection.introspection.get_constraints(
                cursor=None,
                table_name=Movie._meta.db_table,
            )
            self.assertIn(constraint.name, constraint_info)
            self.assertCountEqual(
                constraint_info[constraint.name]["columns"],
                constraint.fields,
            )
            Movie.objects.create(title="Jaws", reviews=[Review(title="Good", rating=1)])
            msg = "embedded_multi_idx dup key: { reviews.rating: 1 }"
            with self.assertRaisesMessage(IntegrityError, msg):
                Movie.objects.create(
                    title="Jaws",
                    reviews=[Review(title="Good", rating=2), Review(title="Bad", rating=1)],
                )
        finally:
            with connection.schema_editor() as editor:
                editor.remove_constraint(constraint=constraint, model=Movie)

    def test_add_constraint_nonexistent_field(self):
        # This case shouldn't happen as it should be caught by system checks
        # before the migrate stage.
        constraint = EmbeddedFieldUniqueConstraint(
            name="embedded_multi_idx",
            fields=["title.xxx"],
        )
        msg = "Movie has no field named 'title.xxx"
        with connection.schema_editor() as editor, self.assertRaisesMessage(FieldDoesNotExist, msg):
            editor.add_constraint(constraint=constraint, model=Movie)
