from django.test import TestCase

from django_mongodb_backend.test import MongoTestCaseMixin

from .models import Book


class UnionTests(MongoTestCaseMixin, TestCase):
    def test_union_simple_conditions(self):
        with self.assertNumQueries(1) as ctx:
            list(Book.objects.filter(title="star wars").union(Book.objects.filter(isbn__in="1234")))
        self.assertAggregateQuery(
            ctx.captured_queries[0]["sql"],
            "queries__book",
            [
                {"$match": {"title": "star wars"}},
                {"$project": {"_id": 1, "author_id": 1, "title": 1, "isbn": 1}},
                {
                    "$unionWith": {
                        "coll": "queries__book",
                        "pipeline": [
                            {"$match": {"isbn": {"$in": ("1", "2", "3", "4")}}},
                            {"$project": {"_id": 1, "author_id": 1, "title": 1, "isbn": 1}},
                        ],
                    }
                },
                {
                    "$group": {
                        "_id": {
                            "_id": "$_id",
                            "author_id": "$author_id",
                            "title": "$title",
                            "isbn": "$isbn",
                        }
                    }
                },
                {
                    "$addFields": {
                        "_id": "$_id._id",
                        "author_id": "$_id.author_id",
                        "title": "$_id.title",
                        "isbn": "$_id.isbn",
                    }
                },
            ],
        )

    def test_union_all_simple_conditions(self):
        with self.assertNumQueries(1) as ctx:
            list(
                Book.objects.filter(title="star wars").union(
                    Book.objects.filter(isbn="1234"), all=True
                )
            )
        self.assertAggregateQuery(
            ctx.captured_queries[0]["sql"],
            "queries__book",
            [
                {"$match": {"title": "star wars"}},
                {"$project": {"_id": 1, "author_id": 1, "title": 1, "isbn": 1}},
                {
                    "$unionWith": {
                        "coll": "queries__book",
                        "pipeline": [
                            {"$match": {"isbn": "1234"}},
                            {"$project": {"_id": 1, "author_id": 1, "title": 1, "isbn": 1}},
                        ],
                    }
                },
            ],
        )
