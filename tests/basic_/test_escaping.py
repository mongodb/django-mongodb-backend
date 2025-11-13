"""Literals that MongoDB intreprets as expressions are escaped."""

from django.test import TestCase

from django_mongodb_backend.test import MongoTestCaseMixin

from .models import Author


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
