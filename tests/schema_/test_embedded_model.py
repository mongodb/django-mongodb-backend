import itertools

from django.db import connection, models
from django.test import TransactionTestCase, skipUnlessDBFeature
from django.test.utils import isolate_apps

from django_mongodb_backend.fields import EmbeddedModelField
from django_mongodb_backend.models import EmbeddedModel

from .models import Address, Author, Book, new_apps


class TestMixin:
    available_apps = []
    models = [Address, Author, Book]

    # Utility functions

    def setUp(self):
        # local_models should contain test dependent model classes that will be
        # automatically removed from the app cache on test tear down.
        self.local_models = []
        # isolated_local_models contains models that are in test methods
        # decorated with @isolate_apps.
        self.isolated_local_models = []

    def tearDown(self):
        # Delete any tables made for our models
        self.delete_tables()
        new_apps.clear_cache()
        for model in new_apps.get_models():
            model._meta._expire_cache()
        if "schema" in new_apps.all_models:
            for model in self.local_models:
                for many_to_many in model._meta.many_to_many:
                    through = many_to_many.remote_field.through
                    if through and through._meta.auto_created:
                        del new_apps.all_models["schema"][through._meta.model_name]
                del new_apps.all_models["schema"][model._meta.model_name]
        if self.isolated_local_models:
            with connection.schema_editor() as editor:
                for model in self.isolated_local_models:
                    editor.delete_model(model)

    def delete_tables(self):
        "Deletes all model tables for our models for a clean test environment"
        converter = connection.introspection.identifier_converter
        with connection.schema_editor() as editor:
            connection.disable_constraint_checking()
            table_names = connection.introspection.table_names()
            if connection.features.ignores_table_name_case:
                table_names = [table_name.lower() for table_name in table_names]
            for model in itertools.chain(SchemaTests.models, self.local_models):
                tbl = converter(model._meta.db_table)
                if connection.features.ignores_table_name_case:
                    tbl = tbl.lower()
                if tbl in table_names:
                    editor.delete_model(model)
                    table_names.remove(tbl)
            connection.enable_constraint_checking()

    def get_constraints(self, table):
        """
        Get the constraints on a table using a new cursor.
        """
        with connection.cursor() as cursor:
            return connection.introspection.get_constraints(cursor, table)

    def get_constraints_for_columns(self, model, columns):
        constraints = self.get_constraints(model._meta.db_table)
        constraints_for_column = []
        for name, details in constraints.items():
            if details["columns"] == columns:
                constraints_for_column.append(name)
        return sorted(constraints_for_column)

    def assertIndexOrder(self, table, index, order):
        constraints = self.get_constraints(table)
        self.assertIn(index, constraints)
        index_orders = constraints[index]["orders"]
        self.assertTrue(
            all(val == expected for val, expected in zip(index_orders, order, strict=True))
        )

    def assertTableExists(self, model):
        self.assertIn(model._meta.db_table, connection.introspection.table_names())

    def assertTableNotExists(self, model):
        self.assertNotIn(model._meta.db_table, connection.introspection.table_names())


class SchemaTests(TestMixin, TransactionTestCase):
    # SchemaEditor.create_model() tests
    def test_db_index(self):
        """Field(db_index=True) on an embedded model."""
        with connection.schema_editor() as editor:
            # Create the table
            editor.create_model(Book)
            # The table is there
            self.assertTableExists(Book)
            # Embedded indexes are created.
            self.assertEqual(
                self.get_constraints_for_columns(Book, ["author.age"]),
                ["schema__book_author.age_dc08100b"],
            )
            self.assertEqual(
                self.get_constraints_for_columns(Book, ["author.address.zip_code"]),
                ["schema__book_author.address.zip_code_7b9a9307"],
            )
            # Clean up that table
            editor.delete_model(Book)
        # The table is gone
        self.assertTableNotExists(Author)

    def test_unique(self):
        """Field(unique=True) on an embedded model."""
        with connection.schema_editor() as editor:
            editor.create_model(Book)
            self.assertTableExists(Book)
            # Embedded uniques are created.
            self.assertEqual(
                self.get_constraints_for_columns(Book, ["author.employee_id"]),
                ["schema__book_author.employee_id_7d4d3eff_uniq"],
            )
            self.assertEqual(
                self.get_constraints_for_columns(Book, ["author.address.uid"]),
                ["schema__book_author.address.uid_8124a01f_uniq"],
            )
            # Clean up that table
            editor.delete_model(Book)
        self.assertTableNotExists(Author)

    @isolate_apps("schema_")
    def test_unique_together(self):
        """Meta.unique_together on an embedded model."""

        class Address(EmbeddedModel):
            unique_together_one = models.CharField(max_length=10)
            unique_together_two = models.CharField(max_length=10)

            class Meta:
                app_label = "schema_"
                unique_together = [("unique_together_one", "unique_together_two")]

        class Author(EmbeddedModel):
            address = EmbeddedModelField(Address)
            unique_together_three = models.CharField(max_length=10)
            unique_together_four = models.CharField(max_length=10)

            class Meta:
                app_label = "schema_"
                unique_together = [("unique_together_three", "unique_together_four")]

        class Book(models.Model):
            author = EmbeddedModelField(Author)

            class Meta:
                app_label = "schema_"

        with connection.schema_editor() as editor:
            editor.create_model(Book)
            self.assertTableExists(Book)
            # Embedded uniques are created.
            self.assertEqual(
                self.get_constraints_for_columns(
                    Book, ["author.unique_together_three", "author.unique_together_four"]
                ),
                [
                    "schema__author_author.unique_together_three_author.unique_together_four_39e1cb43_uniq"
                ],
            )
            self.assertEqual(
                self.get_constraints_for_columns(
                    Book,
                    ["author.address.unique_together_one", "author.address.unique_together_two"],
                ),
                [
                    "schema__address_author.address.unique_together_one_author.address.unique_together_two_de682e30_uniq"
                ],
            )
            editor.delete_model(Book)
        self.assertTableNotExists(Book)

    @isolate_apps("schema_")
    def test_indexes(self):
        """Meta.indexes on an embedded model."""

        class Address(EmbeddedModel):
            indexed_one = models.CharField(max_length=10)

            class Meta:
                app_label = "schema_"
                indexes = [models.Index(fields=["indexed_one"])]

        class Author(EmbeddedModel):
            address = EmbeddedModelField(Address)
            indexed_two = models.CharField(max_length=10)

            class Meta:
                app_label = "schema_"
                indexes = [models.Index(fields=["indexed_two"])]

        class Book(models.Model):
            author = EmbeddedModelField(Author)

            class Meta:
                app_label = "schema_"

        with connection.schema_editor() as editor:
            editor.create_model(Book)
            self.assertTableExists(Book)
            # Embedded uniques are created.
            self.assertEqual(
                self.get_constraints_for_columns(Book, ["author.indexed_two"]),
                ["schema__aut_indexed_b19137_idx"],
            )
            self.assertEqual(
                self.get_constraints_for_columns(
                    Book,
                    ["author.address.indexed_one"],
                ),
                ["schema__add_indexed_b64972_idx"],
            )
            editor.delete_model(Author)
        self.assertTableNotExists(Author)

    @isolate_apps("schema_")
    def test_constraints(self):
        """Meta.constraints on an embedded model."""

        class Address(models.Model):
            unique_constraint_one = models.CharField(max_length=10)

            class Meta:
                app_label = "schema_"
                constraints = [
                    models.UniqueConstraint(fields=["unique_constraint_one"], name="unique_one")
                ]

        class Author(models.Model):
            address = EmbeddedModelField(Address)
            unique_constraint_two = models.CharField(max_length=10)

            class Meta:
                app_label = "schema_"
                constraints = [
                    models.UniqueConstraint(fields=["unique_constraint_two"], name="unique_two")
                ]

        class Book(models.Model):
            author = EmbeddedModelField(Author)

            class Meta:
                app_label = "schema_"

        with connection.schema_editor() as editor:
            editor.create_model(Book)
            self.assertTableExists(Book)
            # Embedded uniques are created.
            self.assertEqual(
                self.get_constraints_for_columns(Book, ["author.unique_constraint_two"]),
                ["unique_two"],
            )
            self.assertEqual(
                self.get_constraints_for_columns(
                    Book,
                    ["author.address.unique_constraint_one"],
                ),
                ["unique_one"],
            )
            editor.delete_model(Author)
        self.assertTableNotExists(Author)

    # SchemaEditor.add_field() / remove_field() tests
    @isolate_apps("schema_")
    def test_add_remove_field_db_index_and_unique(self):
        """AddField/RemoveField + EmbeddedModelField + Field(db_index=True) & Field(unique=True)."""

        class Book(models.Model):
            name = models.CharField(max_length=100)

            class Meta:
                app_label = "schema_"

        new_field = EmbeddedModelField(Author)
        new_field.set_attributes_from_name("author")
        with connection.schema_editor() as editor:
            # Create the table amd add the field.
            editor.create_model(Book)
            editor.add_field(Book, new_field)
            # Embedded indexes are created.
            self.assertEqual(
                self.get_constraints_for_columns(Book, ["author.age"]),
                ["schema__book_author.age_dc08100b"],
            )
            self.assertEqual(
                self.get_constraints_for_columns(Book, ["author.address.zip_code"]),
                ["schema__book_author.address.zip_code_7b9a9307"],
            )
            # Embedded uniques
            self.assertEqual(
                self.get_constraints_for_columns(Book, ["author.employee_id"]),
                ["schema__book_author.employee_id_7d4d3eff_uniq"],
            )
            self.assertEqual(
                self.get_constraints_for_columns(Book, ["author.address.uid"]),
                ["schema__book_author.address.uid_8124a01f_uniq"],
            )
            editor.remove_field(Book, new_field)
            # Embedded indexes are removed.
            self.assertEqual(
                self.get_constraints_for_columns(Book, ["author.age"]),
                [],
            )
            self.assertEqual(
                self.get_constraints_for_columns(Book, ["author.address.zip_code"]),
                [],
            )
            self.assertEqual(
                self.get_constraints_for_columns(Book, ["author.employee_id"]),
                [],
            )
            self.assertEqual(
                self.get_constraints_for_columns(Book, ["author.address.uid"]),
                [],
            )
            editor.delete_model(Book)
        self.assertTableNotExists(Author)

    @isolate_apps("schema_")
    def test_add_remove_field_unique_together(self):
        """AddField/RemoveField + EmbeddedModelField + Meta.unique_together."""

        class Address(models.Model):
            unique_together_one = models.CharField(max_length=10)
            unique_together_two = models.CharField(max_length=10)

            class Meta:
                app_label = "schema_"
                unique_together = [("unique_together_one", "unique_together_two")]

        class Author(models.Model):
            address = EmbeddedModelField(Address)
            unique_together_three = models.CharField(max_length=10)
            unique_together_four = models.CharField(max_length=10)

            class Meta:
                app_label = "schema_"
                unique_together = [("unique_together_three", "unique_together_four")]

        class Book(models.Model):
            author = EmbeddedModelField(Author)

            class Meta:
                app_label = "schema_"

        new_field = EmbeddedModelField(Author)
        new_field.set_attributes_from_name("author")
        with connection.schema_editor() as editor:
            # Create the table and add the field.
            editor.create_model(Book)
            editor.add_field(Book, new_field)
            # Embedded uniques are created.
            self.assertEqual(
                self.get_constraints_for_columns(
                    Book, ["author.unique_together_three", "author.unique_together_four"]
                ),
                [
                    "schema__author_author.unique_together_three_author.unique_together_four_39e1cb43_uniq"
                ],
            )
            self.assertEqual(
                self.get_constraints_for_columns(
                    Book,
                    ["author.address.unique_together_one", "author.address.unique_together_two"],
                ),
                [
                    "schema__address_author.address.unique_together_one_author.address.unique_together_two_de682e30_uniq"
                ],
            )
            editor.remove_field(Book, new_field)
            # Embedded indexes are removed.
            self.assertEqual(
                self.get_constraints_for_columns(
                    Book, ["author.unique_together_three", "author.unique_together_four"]
                ),
                [],
            )
            self.assertEqual(
                self.get_constraints_for_columns(
                    Book,
                    ["author.address.unique_together_one", "author.address.unique_together_two"],
                ),
                [],
            )
            editor.delete_model(Book)
        self.assertTableNotExists(Book)

    @isolate_apps("schema_")
    def test_add_remove_field_indexes(self):
        """AddField/RemoveField + EmbeddedModelField + Meta.indexes."""

        class Address(models.Model):
            indexed_one = models.CharField(max_length=10)

            class Meta:
                app_label = "schema_"
                indexes = [models.Index(fields=["indexed_one"])]

        class Author(models.Model):
            address = EmbeddedModelField(Address)
            indexed_two = models.CharField(max_length=10)

            class Meta:
                app_label = "schema_"
                indexes = [models.Index(fields=["indexed_two"])]

        class Book(models.Model):
            author = EmbeddedModelField(Author)

            class Meta:
                app_label = "schema_"

        new_field = EmbeddedModelField(Author)
        new_field.set_attributes_from_name("author")
        with connection.schema_editor() as editor:
            # Create the table and add the field.
            editor.create_model(Book)
            editor.add_field(Book, new_field)
            # Embedded indexes are created.
            self.assertEqual(
                self.get_constraints_for_columns(Book, ["author.indexed_two"]),
                ["schema__aut_indexed_b19137_idx"],
            )
            self.assertEqual(
                self.get_constraints_for_columns(
                    Book,
                    ["author.address.indexed_one"],
                ),
                ["schema__add_indexed_b64972_idx"],
            )
            editor.remove_field(Book, new_field)
            # Embedded indexes are removed.
            self.assertEqual(
                self.get_constraints_for_columns(Book, ["author.indexed_two"]),
                [],
            )
            self.assertEqual(
                self.get_constraints_for_columns(
                    Book,
                    ["author.address.indexed_one"],
                ),
                [],
            )
            editor.delete_model(Author)
        self.assertTableNotExists(Author)

    @isolate_apps("schema_")
    def test_add_remove_field_constraints(self):
        """AddField/RemoveField + EmbeddedModelField + Meta.constraints."""

        class Address(models.Model):
            unique_constraint_one = models.CharField(max_length=10)

            class Meta:
                app_label = "schema_"
                constraints = [
                    models.UniqueConstraint(fields=["unique_constraint_one"], name="unique_one")
                ]

        class Author(models.Model):
            address = EmbeddedModelField(Address)
            unique_constraint_two = models.CharField(max_length=10)

            class Meta:
                app_label = "schema_"
                constraints = [
                    models.UniqueConstraint(fields=["unique_constraint_two"], name="unique_two")
                ]

        class Book(models.Model):
            author = EmbeddedModelField(Author)

            class Meta:
                app_label = "schema_"

        new_field = EmbeddedModelField(Author)
        new_field.set_attributes_from_name("author")
        with connection.schema_editor() as editor:
            # Create the table and add the field.
            editor.create_model(Book)
            editor.add_field(Book, new_field)
            # Embedded constraints are created.
            self.assertEqual(
                self.get_constraints_for_columns(Book, ["author.unique_constraint_two"]),
                ["unique_two"],
            )
            self.assertEqual(
                self.get_constraints_for_columns(
                    Book,
                    ["author.address.unique_constraint_one"],
                ),
                ["unique_one"],
            )
            editor.remove_field(Book, new_field)
            # Embedded constraints are removed.
            self.assertEqual(
                self.get_constraints_for_columns(Book, ["author.unique_constraint_two"]),
                [],
            )
            self.assertEqual(
                self.get_constraints_for_columns(
                    Book,
                    ["author.address.unique_constraint_one"],
                ),
                [],
            )
            editor.delete_model(Author)
        self.assertTableNotExists(Author)


class EmbeddedModelsIgnoredTests(TestMixin, TransactionTestCase):
    def test_embedded_not_created(self):
        """create_model() and delete_model() ignore EmbeddedModel."""
        with connection.schema_editor() as editor:
            editor.create_model(Book)
            editor.create_model(Address)
            editor.create_model(Author)
            self.assertTableExists(Book)
            self.assertTableNotExists(Address)
            self.assertTableNotExists(Author)
            editor.delete_model(Book)
            with self.assertNumQueries(0):
                editor.delete_model(Address)
                editor.delete_model(Author)
        self.assertTableNotExists(Book)

    def test_embedded_add_field_ignored(self):
        """add_field() and remove_field() ignore EmbeddedModel."""
        new_field = models.CharField(max_length=1, default="a")
        new_field.set_attributes_from_name("char")
        with connection.schema_editor() as editor, self.assertNumQueries(0):
            editor.add_field(Author, new_field)
        with connection.schema_editor() as editor, self.assertNumQueries(0):
            editor.remove_field(Author, new_field)

    def test_embedded_alter_field_ignored(self):
        """alter_field() ignores EmbeddedModel."""
        old_field = models.CharField(max_length=1)
        old_field.set_attributes_from_name("old")
        new_field = models.CharField(max_length=1)
        new_field.set_attributes_from_name("new")
        with connection.schema_editor() as editor, self.assertNumQueries(0):
            editor.alter_field(Author, old_field, new_field)


@skipUnlessDBFeature("gis_enabled")
class GISTests(TestMixin, TransactionTestCase):
    @isolate_apps("schema_")
    def test_create_model(self):
        """
        Spatial indexes for embedded GIS fields are created when the collections are
        created.
        """
        from django.contrib.gis.db.models import PointField  # noqa: PLC0415

        class Place(EmbeddedModel):
            name = models.CharField(max_length=10)
            location = PointField()

            class Meta:
                app_label = "schema_"

        class Author(models.Model):
            birthplace = EmbeddedModelField(Place)

            class Meta:
                app_label = "schema_"

        with connection.schema_editor() as editor:
            # Create the table
            editor.create_model(Author)
            self.assertTableExists(Author)
            # The embedded GEO indexes is created.
            constraint_name = "schema__author_birthplace.location_id"
            self.assertEqual(
                self.get_constraints_for_columns(Author, ["birthplace.location"]),
                [constraint_name],
            )
            self.assertIndexOrder(Author._meta.db_table, constraint_name, ["GEO"])
            editor.delete_model(Author)
        self.assertTableNotExists(Author)
