from bson import ObjectId
from django.db import connection
from django.test import TestCase

from django_mongodb_backend.test import MongoTestCaseMixin

from .models import Book, NullableJSONModel, Number


class NumericLookupTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.objs = Number.objects.bulk_create(Number(num=x) for x in range(5))
        # Null values should be excluded in less than queries.
        Number.objects.create()

    def test_lt(self):
        self.assertQuerySetEqual(Number.objects.filter(num__lt=3), self.objs[:3])

    def test_lte(self):
        self.assertQuerySetEqual(Number.objects.filter(num__lte=3), self.objs[:4])


class RegexTests(MongoTestCaseMixin, TestCase):
    def test_mql(self):
        # $regexMatch must not cast the input to string, otherwise MongoDB
        # can't use the field's indexes.
        with self.assertNumQueries(1) as ctx:
            list(Book.objects.filter(title__regex="Moby Dick"))
        query = ctx.captured_queries[0]["sql"]
        self.assertAggregateQuery(
            query,
            "lookup__book",
            [
                {
                    "$match": {
                        "$expr": {
                            "$regexMatch": {"input": "$title", "regex": "Moby Dick", "options": ""}
                        }
                    }
                }
            ],
        )


class LookupMQLTests(MongoTestCaseMixin, TestCase):
    def test_eq(self):
        with self.assertNumQueries(1) as ctx:
            list(Book.objects.filter(title="Moby Dick"))
        self.assertAggregateQuery(
            ctx.captured_queries[0]["sql"], "lookup__book", [{"$match": {"title": "Moby Dick"}}]
        )

    def test_in(self):
        with self.assertNumQueries(1) as ctx:
            list(Book.objects.filter(title__in=["Moby Dick"]))
        self.assertAggregateQuery(
            ctx.captured_queries[0]["sql"],
            "lookup__book",
            [{"$match": {"title": {"$in": ("Moby Dick",)}}}],
        )

    def test_eq_and_in(self):
        with self.assertNumQueries(1) as ctx:
            list(Book.objects.filter(title="Moby Dick", isbn__in=["12345", "56789"]))
        self.assertAggregateQuery(
            ctx.captured_queries[0]["sql"],
            "lookup__book",
            [{"$match": {"$and": [{"isbn": {"$in": ("12345", "56789")}}, {"title": "Moby Dick"}]}}],
        )


class NullValueLookupTests(MongoTestCaseMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.book_objs = Book.objects.bulk_create(
            Book(title=f"Book {i}", isbn=str(i)) for i in range(5)
        )

        cls.null_objs = NullableJSONModel.objects.bulk_create(NullableJSONModel() for _ in range(5))
        cls.unique_id = ObjectId()
        for model in (Book, NullableJSONModel):
            collection = connection.database.get_collection(model._meta.db_table)
            collection.insert_one({"_id": cls.unique_id})

    def test_none_filter_nullable_json_exact(self):
        with self.assertNumQueries(1) as ctx:
            self.assertQuerySetEqual(
                NullableJSONModel.objects.filter(value=None),
                self.null_objs[:-1],
            )
        self.assertAggregateQuery(
            ctx.captured_queries[0]["sql"],
            "lookup__nullablejsonmodel",
            [{"$match": {"$and": [{"value": {"$exists": True}}, {"value": None}]}}],
        )

    def test_none_filter_nullable_json_in(self):
        with self.assertNumQueries(1) as ctx:
            self.assertQuerySetEqual(
                NullableJSONModel.objects.filter(value__in=[None]),
                self.null_objs[:-1],
            )
        self.assertAggregateQuery(
            ctx.captured_queries[0]["sql"],
            "lookup__nullablejsonmodel",
            [{"$match": {"$and": [{"value": {"$exists": True}}, {"value": {"$in": [None]}}]}}],
        )

    def test_none_filter_binary_operator_exact(self):
        with self.assertNumQueries(1) as ctx:
            self.assertQuerySetEqual(Book.objects.filter(title=None), [])
        self.assertAggregateQuery(
            ctx.captured_queries[0]["sql"],
            "lookup__book",
            [
                {
                    "$match": {
                        "$or": [
                            {"$and": [{"title": {"$exists": True}}, {"title": None}]},
                            {"$expr": {"$eq": [{"$type": "$title"}, "missing"]}},
                        ]
                    }
                }
            ],
        )

    def test_none_filter_binary_operator_in(self):
        with self.assertNumQueries(1) as ctx:
            self.assertQuerySetEqual(Book.objects.filter(title__in=[None]), [])
        self.assertAggregateQuery(
            ctx.captured_queries[0]["sql"],
            "lookup__book",
            [
                {
                    "$match": {
                        "$or": [
                            {"$and": [{"title": {"$exists": True}}, {"title": None}]},
                            {"$expr": {"$eq": [{"$type": "$title"}, "missing"]}},
                        ]
                    }
                }
            ],
        )
