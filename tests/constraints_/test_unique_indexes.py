from django.db import connection, models
from django.test import SimpleTestCase
from django.test.utils import isolate_apps


@isolate_apps("constraints_")
class UniqueIndexTests(SimpleTestCase):
    def test_single_field_unique_index_filter(self):
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

        self.assertEqual(
            dict(index.document["partialFilterExpression"]),
            {"name": {"$gte": "", "$exists": True}},
        )

    def test_multi_field_unique_index_filter(self):
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

        self.assertEqual(
            dict(index.document["partialFilterExpression"]),
            {
                "version": {
                    "$gte": -9223372036854775808,
                    "$lte": 9223372036854775807,
                },
                "name": {"$gte": "", "$exists": True},
            },
        )
