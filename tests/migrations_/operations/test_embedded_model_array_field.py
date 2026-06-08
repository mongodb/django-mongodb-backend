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
from django_mongodb_backend.fields import (
    EmbeddedModelArrayField,
    ObjectIdAutoField,
)


class EmbeddedModelArrayFieldOperationTests(OperationTestBase):
    """Tests for embedded field operations on EmbeddedModelArrayField."""

    available_apps = ["migrations_"]

    def set_up_test_model(self, app_label):
        """Create Book with an EmbeddedModelArrayField pointing to Review."""
        operations = [
            migrations.CreateModel(
                "Review",
                [
                    ("id", ObjectIdAutoField(primary_key=True)),
                    ("body", models.TextField()),
                ],
                options={},
            ),
            migrations.CreateModel(
                "Book",
                [
                    ("id", ObjectIdAutoField(primary_key=True)),
                    ("title", models.CharField(max_length=100)),
                    ("reviews", EmbeddedModelArrayField(f"{app_label}.review")),
                ],
                options={},
            ),
        ]
        return self.apply_operations(app_label, ProjectState(), operations)

    def test_add_embedded_field(self):
        """AddEmbeddedField sets the default on all existing array elements."""
        app_label = "test_arademfl"
        new_field = models.IntegerField(null=True, default=50)
        operation = AddEmbeddedField("Book", "reviews.$[].rating", new_field)
        self.assertEqual(operation.describe(), "Add embedded field reviews.$[].rating to Book")

        initial_state = self.set_up_test_model(app_label)
        Book = initial_state.apps.get_model(app_label, "Book")
        Review = initial_state.apps.get_model(app_label, "Review")
        book = Book.objects.create(
            title="Moby Dick",
            reviews=[Review(body="Classic!")],
        )
        # Add field to the state without touching the database.
        new_state = self.apply_operations(
            app_label,
            initial_state,
            operations=[
                migrations.AddField("Review", "rating", new_field, preserve_default=False),
                operation,
            ],
        )
        Book = new_state.apps.get_model(app_label, "Book")
        book = Book.objects.get(pk=book.pk)
        self.assertEqual(book.reviews[0].rating, 50)

        # Reversal removes the key from existing array elements.
        with connection.schema_editor() as editor:
            operation.database_backwards(app_label, editor, new_state, initial_state)

        # TODO:
        # book.refresh_from_db()
        # self.assertEqual(book.reviews[0].body, "Classic!")
        # self.assertFalse(hasattr(book.reviews[0], "rating"))

    def test_remove_embedded_field(self):
        """
        RemoveEmbeddedField issues $unset with the $[] positional
        operator.
        """
        app_label = "test_arremfl"
        initial_state = self.set_up_test_model(app_label)
        # Extend the state with a rating field without touching the database.
        pre_state = self.apply_operations(
            app_label,
            initial_state,
            operations=[
                migrations.AddField(
                    "Review",
                    "rating",
                    models.IntegerField(null=True),
                    preserve_default=False,
                ),
                AddEmbeddedField("Book", "reviews.$[].rating", models.IntegerField(null=True)),
            ],
        )
        operation = RemoveEmbeddedField("Book", "reviews.rating")
        self.assertEqual(operation.describe(), "Remove embedded field reviews.rating from Book")
        new_state = pre_state.clone()
        operation.state_forwards(app_label, new_state)

        with (
            connection.schema_editor() as editor,
            CaptureQueriesContext(connection) as ctx,
        ):
            operation.database_forwards(app_label, editor, pre_state, new_state)
        self.assertIn(
            "'$unset': {'reviews.$[].rating': ''}",
            ctx.captured_queries[-1]["sql"],
        )

        # Reversal re-adds the field to existing array elements.
        with (
            connection.schema_editor() as editor,
            CaptureQueriesContext(connection) as ctx,
        ):
            operation.database_backwards(app_label, editor, new_state, pre_state)
        self.assertIn(
            "'$set': {'reviews.$[].rating':",
            ctx.captured_queries[-1]["sql"],
        )

    def test_alter_embedded_field(self):
        """
        AlterEmbeddedField uses a $map pipeline (not $rename) for array
        paths.
        """
        app_label = "test_araltemfl"
        new_field = models.TextField(db_column="the_body")
        operation = AlterEmbeddedField("Book", "reviews.body", new_field)
        self.assertEqual(operation.describe(), "Alter embedded field reviews.body on Book")

        initial_state = self.set_up_test_model(app_label)
        new_state = initial_state.clone()
        migrations.AlterField("Review", "body", new_field).state_forwards(app_label, new_state)

        with (
            connection.schema_editor() as editor,
            CaptureQueriesContext(connection) as ctx,
        ):
            operation.database_forwards(app_label, editor, initial_state, new_state)
        sql = ctx.captured_queries[-1]["sql"]
        # Must use $map (not $rename) since $rename doesn't support $[] paths.
        self.assertIn("$map", sql)
        self.assertNotIn("$rename", sql)
        self.assertIn("'input': '$reviews'", sql)
        self.assertIn("'field': 'body'", sql)
        self.assertIn("'the_body': '$$item.body'", sql)

        # Reversal renames back.
        with (
            connection.schema_editor() as editor,
            CaptureQueriesContext(connection) as ctx,
        ):
            operation.database_backwards(app_label, editor, new_state, initial_state)
        sql = ctx.captured_queries[-1]["sql"]
        self.assertIn("$map", sql)
        self.assertIn("'field': 'the_body'", sql)
        self.assertIn("'body': '$$item.the_body'", sql)

    def test_rename_embedded_field(self):
        """RenameEmbeddedField uses a $map pipeline for array paths."""
        app_label = "test_arrnemfl"
        operation = RenameEmbeddedField("Book", "reviews.body", "reviews.content")
        self.assertEqual(
            operation.describe(),
            "Rename embedded field reviews.body on Book to reviews.content",
        )

        initial_state = self.set_up_test_model(app_label)
        new_state = initial_state.clone()
        migrations.RenameField("Review", "body", "content").state_forwards(app_label, new_state)

        with (
            connection.schema_editor() as editor,
            CaptureQueriesContext(connection) as ctx,
        ):
            operation.database_forwards(app_label, editor, initial_state, new_state)
        sql = ctx.captured_queries[-1]["sql"]
        self.assertIn("$map", sql)
        self.assertNotIn("$rename", sql)
        self.assertIn("'field': 'body'", sql)
        self.assertIn("'content': '$$item.body'", sql)

        # Reversal renames back.
        with (
            connection.schema_editor() as editor,
            CaptureQueriesContext(connection) as ctx,
        ):
            operation.database_backwards(app_label, editor, new_state, initial_state)
        sql = ctx.captured_queries[-1]["sql"]
        self.assertIn("$map", sql)
        self.assertIn("'field': 'content'", sql)
        self.assertIn("'body': '$$item.content'", sql)
