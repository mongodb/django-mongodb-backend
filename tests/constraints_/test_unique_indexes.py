from django.db import connection, models
from django.test import SimpleTestCase
from django.test.utils import isolate_apps


@isolate_apps("constraints_")
class UniqueIndexTests(SimpleTestCase):
    def test_single_field_unique_index_has_no_partial_filter_when_not_nullable(self):
        class Author(models.Model):
            name = models.TextField(unique=True)

            class Meta:
                app_label = "constraints_"

        field = Author._meta.get_field("name")
        constraint = models.UniqueConstraint(fields=["name"], name="author_name_uniq")

        with connection.schema_editor() as editor:
            index = constraint.get_pymongo_index_model(
                Author,
                schema_editor=editor,
                field=field,
            )

        self.assertNotIn("partialFilterExpression", index.document)

    def test_multi_field_unique_index_has_no_partial_filter_when_not_nullable(self):
        class Book(models.Model):
            version = models.IntegerField()
            name = models.TextField()

            class Meta:
                app_label = "constraints_"
                constraints = [
                    models.UniqueConstraint(
                        fields=["version", "name"],
                        name="unique_book_version",
                    )
                ]

        constraint = Book._meta.constraints[0]

        with connection.schema_editor() as editor:
            index = constraint.get_pymongo_index_model(Book, schema_editor=editor)

        self.assertNotIn("partialFilterExpression", index.document)

    def test_nullable_unique_index_uses_partial_filter(self):
        class Place(models.Model):
            code = models.TextField(unique=True, null=True)

            class Meta:
                app_label = "constraints_"

        field = Place._meta.get_field("code")
        constraint = models.UniqueConstraint(fields=["code"], name="place_code_uniq")

        with connection.schema_editor() as editor:
            index = constraint.get_pymongo_index_model(
                Place,
                schema_editor=editor,
                field=field,
            )

        self.assertEqual(
            dict(index.document["partialFilterExpression"]),
            {"code": {"$gte": ""}},
        )
