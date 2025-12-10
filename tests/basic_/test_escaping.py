"""Literals that MongoDB intreprets as expressions are escaped."""

from operator import attrgetter

from django.db.models import Value
from django.test import TestCase

from django_mongodb_backend.test import MongoTestCaseMixin

from .models import Author, Blob


class ModelCreationTests(MongoTestCaseMixin, TestCase):
    def test_dollar_prefixed_string(self):
        # No escaping is needed because MongoDB's insert doesn't treat
        # dollar-prefixed strings as expressions.
        with self.assertNumQueries(1) as ctx:
            obj = Author.objects.create(name="$foobar")
        obj.refresh_from_db()
        self.assertEqual(obj.name, "$foobar")
        self.assertInsertQuery(
            ctx.captured_queries[0]["sql"], "basic__author", [{"name": "$foobar"}]
        )


class ModelUpdateTests(MongoTestCaseMixin, TestCase):
    """
    $-prefixed strings and dict/tuples that could be interpreted as expressions
    are escaped in the queries that update model instances.
    """

    def test_dollar_prefixed_string(self):
        obj = Author.objects.create(name="foobar")
        obj.name = "$updated"
        with self.assertNumQueries(1) as ctx:
            obj.save()
        obj.refresh_from_db()
        self.assertEqual(obj.name, "$updated")
        self.assertUpdateQuery(
            ctx.captured_queries[0]["sql"],
            "basic__author",
            {"_id": obj.id},
            [{"$set": {"name": {"$literal": "$updated"}}}],
        )

    def test_dollar_prefixed_value(self):
        obj = Author.objects.create(name="foobar")
        obj.name = Value("$updated")
        with self.assertNumQueries(1) as ctx:
            obj.save()
        obj.refresh_from_db()
        self.assertEqual(obj.name, "$updated")
        self.assertUpdateQuery(
            ctx.captured_queries[0]["sql"],
            "basic__author",
            {"_id": obj.id},
            [{"$set": {"name": {"$literal": "$updated"}}}],
        )

    def test_dict(self):
        obj = Blob.objects.create(name="foobar")
        obj.data = {"$concat": ["$name", "-", "$name"]}
        obj.save()
        obj.refresh_from_db()
        self.assertEqual(obj.data, {"$concat": ["$name", "-", "$name"]})

    def test_dict_value(self):
        obj = Blob.objects.create(name="foobar", data={})
        obj.data = Value({"$concat": ["$name", "-", "$name"]})
        obj.save()
        obj.refresh_from_db()
        self.assertEqual(obj.data, {"$concat": ["$name", "-", "$name"]})

    def test_tuple(self):
        obj = Blob.objects.create(name="foobar")
        obj.data = ("$name", "-", "$name")
        obj.save()
        obj.refresh_from_db()
        self.assertEqual(obj.data, ["$name", "-", "$name"])

    def test_tuple_value(self):
        obj = Blob.objects.create(name="foobar")
        obj.data = Value(("$name", "-", "$name"))
        obj.save()
        obj.refresh_from_db()
        self.assertEqual(obj.data, ["$name", "-", "$name"])


class AnnotationTests(MongoTestCaseMixin, TestCase):
    def test_dollar_prefixed_value(self):
        """Value() escapes dollar prefixed strings."""
        Author.objects.create(name="Gustavo")
        with self.assertNumQueries(1) as ctx:
            qs = list(Author.objects.annotate(a_value=Value("$name")))
        self.assertQuerySetEqual(qs, ["$name"], attrgetter("a_value"))
        self.assertAggregateQuery(
            ctx.captured_queries[0]["sql"],
            "basic__author",
            [{"$project": {"a_value": {"$literal": "$name"}, "_id": 1, "name": 1}}],
        )
