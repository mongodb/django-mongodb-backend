from django.core.exceptions import FieldDoesNotExist
from django.db import connection
from django.test import SimpleTestCase, TestCase

from django_mongodb_backend.indexes import EmbeddedFieldIndex

from .models import DataHolder, Movie, Owner, Person, Store
from .test_base import SchemaAssertionMixin


class EmbeddedFieldIndexNameTests(SimpleTestCase):
    class LongDBTableModel:
        class _meta:
            db_table = "a_really_very_very_long_model_db_table_name"

    def test_long_db_table(self):
        # Long db_table is truncated.
        index = EmbeddedFieldIndex(fields=["some_really_long_field_name"])
        index.set_name_with_model(self.LongDBTableModel)
        self.assertEqual(index.name, "a_really_ve_some_re_6fc5be_idx")

    def test_starting_char(self):
        # Index name must not start with underscore/number even if db_table
        # does.
        class BadModel:
            class _meta:
                db_table = "_1bad_table"

        index = EmbeddedFieldIndex(fields=["field"])
        index.set_name_with_model(BadModel)
        self.assertEqual(index.name, "D1bad_table_field_eb7c16_idx")


class EmbeddedFieldIndexSchemaTests(SchemaAssertionMixin, TestCase):
    def test_embedded_model_subfield(self):
        index = EmbeddedFieldIndex(name="embedded_idx", fields=["data.integer"])
        with connection.schema_editor() as editor:
            editor.add_index(index=index, model=DataHolder)
        try:
            index_info = connection.introspection.get_constraints(
                cursor=None,
                table_name=DataHolder._meta.db_table,
            )
            self.assertIn(index.name, index_info)
            self.assertCountEqual(index_info[index.name]["columns"], index.fields)
            self.assertEqual(index_info[index.name]["type"], "idx")
        finally:
            with connection.schema_editor() as editor:
                editor.remove_index(index=index, model=DataHolder)

    def test_multiple_fields(self):
        index = EmbeddedFieldIndex(
            name="embedded_multi_idx",
            fields=["integer", "data.integer", "data.string"],
        )
        with connection.schema_editor() as editor:
            editor.add_index(index=index, model=DataHolder)
        try:
            index_info = connection.introspection.get_constraints(
                cursor=None,
                table_name=DataHolder._meta.db_table,
            )
            self.assertIn(index.name, index_info)
            self.assertCountEqual(
                index_info[index.name]["columns"],
                [*index.fields[:-1], "data.string_"],
            )
        finally:
            with connection.schema_editor() as editor:
                editor.remove_index(index=index, model=DataHolder)

    def test_embedded_model_array_subfield(self):
        index = EmbeddedFieldIndex(name="embedded_idx", fields=["reviews.rating"])
        with connection.schema_editor() as editor:
            editor.add_index(index=index, model=Movie)
        try:
            index_info = connection.introspection.get_constraints(
                cursor=None,
                table_name=Movie._meta.db_table,
            )
            self.assertIn(index.name, index_info)
            self.assertCountEqual(index_info[index.name]["columns"], index.fields)
        finally:
            with connection.schema_editor() as editor:
                editor.remove_index(index=index, model=Movie)

    def test_polymorphic_embedded_model_subfield(self):
        index = EmbeddedFieldIndex(name="embedded_idx", fields=["pet.name"])
        with connection.schema_editor() as editor:
            editor.add_index(index=index, model=Person)
        try:
            index_info = connection.introspection.get_constraints(
                cursor=None,
                table_name=Person._meta.db_table,
            )
            self.assertIn(index.name, index_info)
            self.assertCountEqual(index_info[index.name]["columns"], index.fields)
            self.assertEqual(index_info[index.name]["type"], "idx")
        finally:
            with connection.schema_editor() as editor:
                editor.remove_index(index=index, model=Person)

    def test_polymorphic_embedded_model_nonshared_subfield(self):
        """
        Fields that don't exist on all polymorphic embedded models can be
        indexed. In this case, Cat.weight is the second embedded model.
        """
        index = EmbeddedFieldIndex(name="embedded_idx", fields=["pet.weight"])
        with connection.schema_editor() as editor:
            editor.add_index(index=index, model=Person)
        try:
            index_info = connection.introspection.get_constraints(
                cursor=None,
                table_name=Person._meta.db_table,
            )
            self.assertIn(index.name, index_info)
            self.assertCountEqual(index_info[index.name]["columns"], index.fields)
            self.assertEqual(index_info[index.name]["type"], "idx")
        finally:
            with connection.schema_editor() as editor:
                editor.remove_index(index=index, model=Person)

    def test_polymorphic_embedded_model_array_subfield(self):
        index = EmbeddedFieldIndex(name="embedded_idx", fields=["pets.name"])
        with connection.schema_editor() as editor:
            editor.add_index(index=index, model=Owner)
        try:
            index_info = connection.introspection.get_constraints(
                cursor=None,
                table_name=Owner._meta.db_table,
            )
            self.assertIn(index.name, index_info)
            self.assertCountEqual(index_info[index.name]["columns"], index.fields)
        finally:
            with connection.schema_editor() as editor:
                editor.remove_index(index=index, model=Owner)

    def test_polymorphic_embedded_model_aray_nonshared_subfield(self):
        """
        Fields that don't exist on all polymorphic embedded models can be
        indexed. In this case, Cat.weight is the second embedded model.
        """
        index = EmbeddedFieldIndex(name="embedded_idx", fields=["pets.weight"])
        with connection.schema_editor() as editor:
            editor.add_index(index=index, model=Owner)
        try:
            index_info = connection.introspection.get_constraints(
                cursor=None,
                table_name=Owner._meta.db_table,
            )
            self.assertIn(index.name, index_info)
            self.assertCountEqual(index_info[index.name]["columns"], index.fields)
            self.assertEqual(index_info[index.name]["type"], "idx")
        finally:
            with connection.schema_editor() as editor:
                editor.remove_index(index=index, model=Owner)

    def test_nested_polymorphic_embedded_array_subfield(self):
        """Traversing PolymorphicEmbeddedModelField + EmbeddModelArrayField"""
        index = EmbeddedFieldIndex(name="embedded_idx", fields=["thing.tags.name"])
        with connection.schema_editor() as editor:
            editor.add_index(index=index, model=Store)
        try:
            index_info = connection.introspection.get_constraints(
                cursor=None,
                table_name=Store._meta.db_table,
            )
            self.assertIn(index.name, index_info)
            self.assertCountEqual(index_info[index.name]["columns"], index.fields)
            self.assertEqual(index_info[index.name]["type"], "idx")
        finally:
            with connection.schema_editor() as editor:
                editor.remove_index(index=index, model=Store)


class AddIndexNonexistentFieldTests(TestCase):
    # These cases shouldn't happen as they should be caught by system checks
    # before the migrate stage. Nonetheless, it could be useful to have helpful
    # error messages.

    def test_field(self):
        index = EmbeddedFieldIndex(name="name", fields=["xxx"])
        msg = "Movie has no field named 'xxx"
        with connection.schema_editor() as editor, self.assertRaisesMessage(FieldDoesNotExist, msg):
            editor.add_index(index=index, model=Movie)

    def test_field_with_dot(self):
        index = EmbeddedFieldIndex(name="name", fields=["title.xxx"])
        msg = "Movie has no field named 'title.xxx"
        with connection.schema_editor() as editor, self.assertRaisesMessage(FieldDoesNotExist, msg):
            editor.add_index(index=index, model=Movie)

    def test_embedded_subfield(self):
        index = EmbeddedFieldIndex(name="name", fields=["reviews.xxx"])
        msg = "Review has no field named 'xxx"
        with connection.schema_editor() as editor, self.assertRaisesMessage(FieldDoesNotExist, msg):
            editor.add_index(index=index, model=Movie)

    def test_polymorphic_subfield(self):
        index = EmbeddedFieldIndex(name="name", fields=["pet.xxx"])
        msg = "The models of field 'pet' have no field named 'xxx'"
        with connection.schema_editor() as editor, self.assertRaisesMessage(FieldDoesNotExist, msg):
            editor.add_index(index=index, model=Person)

    def test_nested_polymorphic_embedded_array_subfield(self):
        index = EmbeddedFieldIndex(name="name", fields=["thing.tags.xxx"])
        msg = "The models of field 'thing.tags' have no field named 'xxx'."
        with connection.schema_editor() as editor, self.assertRaisesMessage(FieldDoesNotExist, msg):
            editor.add_index(index=index, model=Store)
