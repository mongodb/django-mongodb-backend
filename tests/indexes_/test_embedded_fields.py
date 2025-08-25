from django.core.exceptions import FieldDoesNotExist
from django.db import connection
from django.test import SimpleTestCase, TestCase

from django_mongodb_backend.indexes import EmbeddedFieldIndex

from .models import DataHolder, Movie
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

    def test_add_index_nonexistent_field(self):
        # This case shouldn't happen as it should be caught by system checks
        # before the migrate stage.
        index = EmbeddedFieldIndex(name="embedded_multi_idx", fields=["title.xxx"])
        msg = "Movie has no field named 'title.xxx"
        with connection.schema_editor() as editor, self.assertRaisesMessage(FieldDoesNotExist, msg):
            editor.add_index(index=index, model=Movie)
