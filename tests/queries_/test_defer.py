from django.test import TestCase

from django_mongodb_backend.test import MongoTestCaseMixin

from .models import Author, Book


class DeferTests(MongoTestCaseMixin, TestCase):
    def test_defer(self):
        with self.assertNumQueries(1) as ctx:
            list(Author.objects.defer("name"))
        self.assertAggregateQuery(
            ctx.captured_queries[0]["sql"],
            "queries__author",
            [{"$project": {"_id": 1}}],
        )

    def test_only(self):
        with self.assertNumQueries(1) as ctx:
            list(Book.objects.only("title"))
        self.assertAggregateQuery(
            ctx.captured_queries[0]["sql"],
            "queries__book",
            [{"$project": {"_id": 1, "title": 1}}],
        )
