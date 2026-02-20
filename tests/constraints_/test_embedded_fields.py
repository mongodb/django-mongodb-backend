from django.core.exceptions import FieldDoesNotExist
from django.db import IntegrityError, connection
from django.test import TestCase

from django_mongodb_backend.constraints import EmbeddedFieldUniqueConstraint

from .models import Address, Cat, Data, DataHolder, Dog, Movie, Owner, Person, Review, Store, Tag


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

    def test_polymorphic_embedded_model_subfield(self):
        constraint = EmbeddedFieldUniqueConstraint(
            name="embedded_created_constraint",
            fields=["pet.name"],
        )
        with connection.schema_editor() as editor:
            editor.add_constraint(constraint=constraint, model=Person)
        try:
            constraint_info = connection.introspection.get_constraints(
                cursor=None,
                table_name=Person._meta.db_table,
            )
            self.assertIn(constraint.name, constraint_info)
            self.assertCountEqual(
                constraint_info[constraint.name]["columns"],
                constraint.fields,
            )
            self.assertEqual(constraint_info[constraint.name]["type"], "idx")
            Person.objects.create(pet=Dog(name="Woofer"))
            msg = 'embedded_created_constraint dup key: { pet.name: "Woofer"'
            with self.assertRaisesMessage(IntegrityError, msg):
                Person.objects.create(pet=Dog(name="Woofer"))
        finally:
            with connection.schema_editor() as editor:
                editor.remove_constraint(constraint=constraint, model=Person)

    def test_polymorphic_embedded_model_nonshared_subfield(self):
        constraint = EmbeddedFieldUniqueConstraint(
            name="embedded_created_constraint",
            fields=["pet.weight"],
        )
        with connection.schema_editor() as editor:
            editor.add_constraint(constraint=constraint, model=Person)
        try:
            constraint_info = connection.introspection.get_constraints(
                cursor=None,
                table_name=Person._meta.db_table,
            )
            self.assertIn(constraint.name, constraint_info)
            self.assertCountEqual(
                constraint_info[constraint.name]["columns"],
                constraint.fields,
            )
            self.assertEqual(constraint_info[constraint.name]["type"], "idx")
            Person.objects.create(pet=Cat(name="Pheobe", weight="10"))
            msg = "embedded_created_constraint dup key: { pet.weight: 10 }"
            with self.assertRaisesMessage(IntegrityError, msg):
                Person.objects.create(pet=Cat(name="Pheobe", weight="10"))
        finally:
            with connection.schema_editor() as editor:
                editor.remove_constraint(constraint=constraint, model=Person)

    def test_polymorphic_embedded_model_array_subfield(self):
        constraint = EmbeddedFieldUniqueConstraint(
            name="embedded_created_constraint",
            fields=["pets.name"],
        )
        with connection.schema_editor() as editor:
            editor.add_constraint(constraint=constraint, model=Owner)
        try:
            constraint_info = connection.introspection.get_constraints(
                cursor=None,
                table_name=Owner._meta.db_table,
            )
            self.assertIn(constraint.name, constraint_info)
            self.assertCountEqual(
                constraint_info[constraint.name]["columns"],
                constraint.fields,
            )
            self.assertEqual(constraint_info[constraint.name]["type"], "idx")
            Owner.objects.create(pets=[Dog(name="Woofer")])
            msg = 'embedded_created_constraint dup key: { pets.name: "Woofer"'
            with self.assertRaisesMessage(IntegrityError, msg):
                Owner.objects.create(pets=[Dog(name="Woofer")])
        finally:
            with connection.schema_editor() as editor:
                editor.remove_constraint(constraint=constraint, model=Owner)

    def test_polymorphic_embedded_model_array_nonshared_subfield(self):
        constraint = EmbeddedFieldUniqueConstraint(
            name="embedded_created_constraint",
            fields=["pets.weight"],
        )
        with connection.schema_editor() as editor:
            editor.add_constraint(constraint=constraint, model=Owner)
        try:
            constraint_info = connection.introspection.get_constraints(
                cursor=None,
                table_name=Owner._meta.db_table,
            )
            self.assertIn(constraint.name, constraint_info)
            self.assertCountEqual(
                constraint_info[constraint.name]["columns"],
                constraint.fields,
            )
            self.assertEqual(constraint_info[constraint.name]["type"], "idx")
            Owner.objects.create(pets=[Cat(name="Pheobe", weight="10")])
            msg = "embedded_created_constraint dup key: { pets.weight: 10 }"
            with self.assertRaisesMessage(IntegrityError, msg):
                Owner.objects.create(pets=[Cat(name="Pheobe", weight="10")])
        finally:
            with connection.schema_editor() as editor:
                editor.remove_constraint(constraint=constraint, model=Owner)

    def test_nested_polymorphic_embedded_array_subfield(self):
        """Traversing PolymorphicEmbeddedModelField + EmbeddModelArrayField"""
        constraint = EmbeddedFieldUniqueConstraint(name="name", fields=["thing.tags.name"])
        with connection.schema_editor() as editor:
            editor.add_constraint(constraint=constraint, model=Store)
        try:
            constraint_info = connection.introspection.get_constraints(
                cursor=None,
                table_name=Store._meta.db_table,
            )
            self.assertIn(constraint.name, constraint_info)
            self.assertCountEqual(
                constraint_info[constraint.name]["columns"],
                constraint.fields,
            )
            self.assertEqual(constraint_info[constraint.name]["type"], "idx")
            Store.objects.create(thing=Address(tags=[Tag(name="dup")]))
            msg = 'name dup key: { thing.tags.name: "dup" }'
            with self.assertRaisesMessage(IntegrityError, msg):
                Store.objects.create(thing=Address(tags=[Tag(name="dup")]))
        finally:
            with connection.schema_editor() as editor:
                editor.remove_constraint(constraint=constraint, model=Store)


class AddConstraintNonexistentFieldTests(TestCase):
    # These cases shouldn't happen as they should be caught by system checks
    # before the migrate stage. Nonetheless, it could be useful to have helpful
    # error messages.

    def test_field(self):
        constraint = EmbeddedFieldUniqueConstraint(name="name", fields=["xxx"])
        msg = "Movie has no field named 'xxx"
        with connection.schema_editor() as editor, self.assertRaisesMessage(FieldDoesNotExist, msg):
            editor.add_constraint(constraint=constraint, model=Movie)

    def test_field_with_dot(self):
        constraint = EmbeddedFieldUniqueConstraint(name="name", fields=["title.xxx"])
        msg = "Movie has no field named 'title.xxx"
        with connection.schema_editor() as editor, self.assertRaisesMessage(FieldDoesNotExist, msg):
            editor.add_constraint(constraint=constraint, model=Movie)

    def test_embedded_subfield(self):
        constraint = EmbeddedFieldUniqueConstraint(name="name", fields=["reviews.xxx"])
        msg = "Review has no field named 'xxx"
        with connection.schema_editor() as editor, self.assertRaisesMessage(FieldDoesNotExist, msg):
            editor.add_constraint(constraint=constraint, model=Movie)

    def test_polymorphic_subfield(self):
        constraint = EmbeddedFieldUniqueConstraint(name="name", fields=["pet.xxx"])
        msg = "The models of field 'pet' have no field named 'xxx'."
        with connection.schema_editor() as editor, self.assertRaisesMessage(FieldDoesNotExist, msg):
            editor.add_constraint(constraint=constraint, model=Person)

    def test_nested_polymorphic_embedded_array_subfield(self):
        constraint = EmbeddedFieldUniqueConstraint(name="name", fields=["thing.tags.xxx"])
        msg = "The models of field 'thing.tags' have no field named 'xxx'."
        with connection.schema_editor() as editor, self.assertRaisesMessage(FieldDoesNotExist, msg):
            editor.add_constraint(constraint=constraint, model=Store)
