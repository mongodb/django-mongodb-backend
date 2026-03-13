from django.db import connection, migrations, models
from django.db.migrations.state import ProjectState
from django.test.utils import CaptureQueriesContext
from migrations.test_base import OperationTestBase

from django_mongodb_backend.db.migrations.operations import (
    AddEmbeddedField,
    AlterEmbeddedField,
    RemoveEmbeddedField,
    RenameEmbeddedField,
)
from django_mongodb_backend.fields import EmbeddedModelField, ObjectIdAutoField


class OperationTests(OperationTestBase):
    """
    Tests running the operations and making sure they do what they say they do.
    Each test looks at their state changing, and then their database operation,
    both forwards and backwards.
    """

    available_apps = ["migrations_"]

    #    def make_test_state(self, app_label, operation, **kwargs):
    #        """
    #        Makes a test state using set_up_test_model and returns the
    #        original state and the state after the migration is applied.
    #        """
    #        project_state = self.set_up_test_model(app_label, **kwargs)
    #        new_state = project_state.clone()
    #        operation.state_forwards(app_label, new_state)
    #        return project_state, new_state

    def set_up_test_model(self, app_label):
        """Create a test model state and database table."""
        # Make the "current" state.
        operations = [
            migrations.CreateModel(
                "Author",
                [
                    ("id", ObjectIdAutoField(primary_key=True)),
                    ("name", models.CharField(max_length=100)),
                ],
                options={},
            ),
            migrations.CreateModel(
                "Book",
                [
                    ("id", ObjectIdAutoField(primary_key=True)),
                    ("name", models.CharField(max_length=100)),
                    ("author", EmbeddedModelField("Author")),
                ],
                options={},
            ),
        ]
        return self.apply_operations(app_label, ProjectState(), operations)

    def test_add_embedded_field(self):
        """Test the AddEmbeddedField operation."""
        app_label = "test_ademfl"
        # Test the state alteration
        new_field = models.IntegerField(null=True, default=50)
        operation = AddEmbeddedField(
            "Book",
            "author.age",
            new_field,
        )
        self.assertEqual(operation.describe(), "Add embedded field author.age to Book")
        self.assertEqual(
            operation.formatted_description(), "+ Add embedded field author.age to Book"
        )
        self.assertEqual(operation.migration_name_fragment, "book_author.age")

        initial_state = self.set_up_test_model(app_label)
        # Create initial data
        Book = initial_state.apps.get_model(app_label, "Book")
        Author = initial_state.apps.get_model(app_label, "Author")
        book = Book.objects.create(name="Moby Dick", author=Author(name="Melville"))

        new_state = self.apply_operations(
            app_label,
            initial_state,
            operations=[
                migrations.AddField(
                    "Author",
                    "age",
                    new_field,
                    preserve_default=False,
                ),
                operation,
            ],
        )
        field = new_state.models[app_label, "author"].fields["age"]
        self.assertEqual(field.default, models.NOT_PROVIDED)

        Book = new_state.apps.get_model(app_label, "Book")
        Author = new_state.apps.get_model(app_label, "Author")
        book = Book.objects.get(pk=book.pk)
        # Value is populated on existing columns.
        self.assertEqual(book.author.age, 50)
        # Reversal removes key in exiting documents.
        with connection.schema_editor() as editor:
            operation.database_backwards(app_label, editor, new_state, initial_state)

        b1 = Book.objects.get(pk=book.pk)
        self.assertEqual(b1.author.age, models.NOT_PROVIDED)
        # And deconstruction
        name, args, kwargs = operation.deconstruct()
        self.assertEqual(name, "AddEmbeddedField")
        self.assertEqual(args, [])
        self.assertEqual(kwargs, {"model_name": "Book", "name": "author.age", "field": new_field})

    def test_alter_embedded_field(self):
        """Test the AlterEmbeddedField operation."""
        app_label = "test_altemfl"
        new_field = models.CharField(max_length=100, db_column="the_name")
        operation = AlterEmbeddedField("Book", "author.name", new_field)
        self.assertEqual(operation.describe(), "Alter embedded field author.name on Book")
        self.assertEqual(
            operation.formatted_description(),
            "~ Alter embedded field author.name on Book",
        )
        initial_state = self.set_up_test_model(app_label)
        # Build the new state by updating Author.name's db_column without touching the db.
        new_state = initial_state.clone()
        migrations.AlterField("Author", "name", new_field).state_forwards(app_label, new_state)
        # Test the database alteration.
        with (
            connection.schema_editor() as editor,
            CaptureQueriesContext(connection) as ctx,
        ):
            operation.database_forwards(app_label, editor, initial_state, new_state)
        self.assertEqual(
            ctx.captured_queries[-1]["sql"],
            "db.test_altemfl_book.update_many({}, {'$rename': {'author.name': 'author.the_name'}})",
        )
        # Test reversal.
        with (
            connection.schema_editor() as editor,
            CaptureQueriesContext(connection) as ctx,
        ):
            operation.database_backwards(app_label, editor, new_state, initial_state)
        self.assertEqual(
            ctx.captured_queries[-1]["sql"],
            "db.test_altemfl_book.update_many({}, {'$rename': {'author.the_name': 'author.name'}})",
        )
        # Test deconstruction.
        name, args, kwargs = operation.deconstruct()
        self.assertEqual(name, "AlterEmbeddedField")
        self.assertEqual(args, [])
        self.assertEqual(kwargs, {"model_name": "Book", "name": "author.name", "field": new_field})

    def test_rename_embedded_field(self):
        """Test the RenameEmbeddedField operation."""
        app_label = "test_rnemfl"
        operation = RenameEmbeddedField("Book", "author.name", "author.full_name")
        self.assertEqual(
            operation.describe(),
            "Rename embedded field author.name on Book to author.full_name",
        )
        self.assertEqual(
            operation.formatted_description(),
            "~ Rename embedded field author.name on Book to author.full_name",
        )
        initial_state = self.set_up_test_model(app_label)
        # Build the new state by renaming Author.name to Author.full_name without touching the db.
        new_state = initial_state.clone()
        migrations.RenameField("Author", "name", "full_name").state_forwards(app_label, new_state)
        # Test the database alteration.
        with (
            connection.schema_editor() as editor,
            CaptureQueriesContext(connection) as ctx,
        ):
            operation.database_forwards(app_label, editor, initial_state, new_state)
        self.assertEqual(
            ctx.captured_queries[-1]["sql"],
            "db.test_rnemfl_book.update_many({}, {'$rename': {'author.name': 'author.full_name'}})",
        )
        # Test reversal.
        with (
            connection.schema_editor() as editor,
            CaptureQueriesContext(connection) as ctx,
        ):
            operation.database_backwards(app_label, editor, new_state, initial_state)
        self.assertEqual(
            ctx.captured_queries[-1]["sql"],
            "db.test_rnemfl_book.update_many({}, {'$rename': {'author.full_name': 'author.name'}})",
        )
        # Test deconstruction.
        name, args, kwargs = operation.deconstruct()
        self.assertEqual(name, "RenameEmbeddedField")
        self.assertEqual(args, [])
        self.assertEqual(
            kwargs,
            {"model_name": "Book", "old_name": "author.name", "new_name": "author.full_name"},
        )

    def test_remove_embedded_field(self):
        """Test the RemoveEmbeddedField operation."""
        app_label = "test_rmemfl"
        project_state = self.set_up_test_model(app_label)
        # Test the state alteration
        operation = RemoveEmbeddedField("Book", "author.name")
        self.assertEqual(operation.describe(), "Remove embedded field author.name from Book")
        self.assertEqual(
            operation.formatted_description(), "- Remove embedded field author.name from Book"
        )
        self.assertEqual(operation.migration_name_fragment, "remove_book_author.name")
        new_state = project_state.clone()
        operation.state_forwards(app_label, new_state)
        # Test the database alteration
        with (
            connection.schema_editor() as editor,
            CaptureQueriesContext(connection) as ctx,
        ):
            operation.database_forwards(app_label, editor, project_state, new_state)
        self.assertEqual(
            ctx.captured_queries[-1]["sql"],
            "db.test_rmemfl_book.update_many({}, {'$unset': {'author.name': ''}})",
        )
        # And test reversal
        with (
            connection.schema_editor() as editor,
            CaptureQueriesContext(connection) as ctx,
        ):
            operation.database_backwards(app_label, editor, new_state, project_state)
        self.assertEqual(
            ctx.captured_queries[-1]["sql"],
            "db.test_rmemfl_book.update_many({}, [{'$set': {'author.name': None}}])",
        )
        # And deconstruction
        definition = operation.deconstruct()
        self.assertEqual(definition[0], "RemoveEmbeddedField")
        self.assertEqual(definition[1], [])
        self.assertEqual(definition[2], {"model_name": "Book", "name": "author.name"})
