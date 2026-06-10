import datetime
import sys

from bson.decimal128 import Decimal128
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
            {"name": {"$gte": ""}},
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
                    "$gte": -sys.float_info.max,
                    "$lte": sys.float_info.max,
                },
                "name": {"$gte": ""},
            },
        )

    def test_single_field_small_integer_unique_index_filter(self):
        class Inventory(models.Model):
            count = models.SmallIntegerField(unique=True)

            class Meta:
                app_label = "constraints_"

        field = Inventory._meta.get_field("count")
        constraint = models.UniqueConstraint(fields=["count"], name="inventory_count_uniq")

        with connection.schema_editor() as editor:
            index = constraint.get_pymongo_index_model(
                Inventory,
                schema_editor=editor,
                field=field,
            )

        self.assertEqual(
            dict(index.document["partialFilterExpression"]),
            {
                "count": {
                    "$gte": -2147483648,
                    "$lte": 2147483647,
                }
            },
        )

    def test_single_field_float_unique_index_filter(self):
        class Measurement(models.Model):
            value = models.FloatField(unique=True)

            class Meta:
                app_label = "constraints_"

        field = Measurement._meta.get_field("value")
        constraint = models.UniqueConstraint(fields=["value"], name="measurement_value_uniq")

        with connection.schema_editor() as editor:
            index = constraint.get_pymongo_index_model(
                Measurement,
                schema_editor=editor,
                field=field,
            )

        self.assertEqual(
            dict(index.document["partialFilterExpression"]),
            {
                "value": {
                    "$gte": -sys.float_info.max,
                    "$lte": sys.float_info.max,
                }
            },
        )

    def test_single_field_decimal_unique_index_filter(self):
        class Price(models.Model):
            amount = models.DecimalField(max_digits=6, decimal_places=2, unique=True)

            class Meta:
                app_label = "constraints_"

        field = Price._meta.get_field("amount")
        constraint = models.UniqueConstraint(fields=["amount"], name="price_amount_uniq")

        with connection.schema_editor() as editor:
            index = constraint.get_pymongo_index_model(
                Price,
                schema_editor=editor,
                field=field,
            )

        self.assertEqual(
            dict(index.document["partialFilterExpression"]),
            {
                "amount": {
                    "$gte": Decimal128("-9999999999999999999999999999999999E6111"),
                    "$lte": Decimal128("9999999999999999999999999999999999E6111"),
                }
            },
        )

    def test_single_field_boolean_unique_index_filter(self):
        class Flag(models.Model):
            enabled = models.BooleanField(unique=True)

            class Meta:
                app_label = "constraints_"

        field = Flag._meta.get_field("enabled")
        constraint = models.UniqueConstraint(fields=["enabled"], name="flag_enabled_uniq")

        with connection.schema_editor() as editor:
            index = constraint.get_pymongo_index_model(
                Flag,
                schema_editor=editor,
                field=field,
            )

        self.assertEqual(
            dict(index.document["partialFilterExpression"]),
            {"enabled": {"$in": [True, False]}},
        )

    def test_single_field_date_unique_index_filter(self):
        class Event(models.Model):
            starts_on = models.DateField(unique=True)

            class Meta:
                app_label = "constraints_"

        field = Event._meta.get_field("starts_on")
        constraint = models.UniqueConstraint(fields=["starts_on"], name="event_starts_on_uniq")

        with connection.schema_editor() as editor:
            index = constraint.get_pymongo_index_model(
                Event,
                schema_editor=editor,
                field=field,
            )

        self.assertEqual(
            dict(index.document["partialFilterExpression"]),
            {
                "starts_on": {
                    "$gte": datetime.datetime.min,
                    "$lte": datetime.datetime.max,
                }
            },
        )

    def test_single_field_fallback_unique_index_filter(self):
        class Document(models.Model):
            payload = models.JSONField(unique=True)

            class Meta:
                app_label = "constraints_"

        field = Document._meta.get_field("payload")
        constraint = models.UniqueConstraint(fields=["payload"], name="document_payload_uniq")

        with connection.schema_editor() as editor:
            index = constraint.get_pymongo_index_model(
                Document,
                schema_editor=editor,
                field=field,
            )

        self.assertEqual(
            dict(index.document["partialFilterExpression"]),
            {"payload": {"$type": "object"}},
        )
