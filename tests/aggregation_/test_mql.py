from bson import SON
from django.db.models import Avg
from django.test import TestCase

from django_mongodb_backend.test import MongoTestCaseMixin

from .models import Author


class AggregationMQLTests(MongoTestCaseMixin, TestCase):
    def test_group_by_with_having(self):
        with self.assertNumQueries(1) as ctx:
            list(Author.objects.values("name").annotate(avg_age=Avg("age")).filter(avg_age__gt=10))
        self.assertAggregateQuery(
            ctx.captured_queries[0]["sql"],
            "aggregation__author",
            [
                {
                    "$group": {
                        "__aggregation1": {"$avg": "$age"},
                        "_id": {"name": "$name"},
                        "avg_age": {"$avg": "$age"},
                    }
                },
                {"$addFields": {"name": "$_id.name"}},
                {"$unset": "_id"},
                {"$match": {"__aggregation1": {"$gt": 10.0}}},
                {"$project": {"avg_age": "$__aggregation1", "name": 1}},
            ],
        )

    def test_group_by_with_order_by(self):
        with self.assertNumQueries(1) as ctx:
            list(Author.objects.values("name").annotate(avg_age=Avg("age")).order_by("avg_age"))
        self.assertAggregateQuery(
            ctx.captured_queries[0]["sql"],
            "aggregation__author",
            [
                {
                    "$group": {
                        "__aggregation1": {"$avg": "$age"},
                        "_id": {"name": "$name"},
                        "avg_age": {"$avg": "$age"},
                    }
                },
                {"$addFields": {"name": "$_id.name"}},
                {"$unset": "_id"},
                {"$project": {"avg_age": "$__aggregation1", "name": 1}},
                {"$sort": SON([("avg_age", 1)])},
            ],
        )

    def test_group_by_with_having_and_order_by(self):
        with self.assertNumQueries(1) as ctx:
            list(
                Author.objects.values("name")
                .annotate(avg_age=Avg("age"))
                .filter(avg_age__gt=10)
                .order_by("avg_age")
            )
        self.assertAggregateQuery(
            ctx.captured_queries[0]["sql"],
            "aggregation__author",
            [
                {
                    "$group": {
                        "__aggregation1": {"$avg": "$age"},
                        "__aggregation2": {"$avg": "$age"},
                        "_id": {"name": "$name"},
                        "avg_age": {"$avg": "$age"},
                    }
                },
                {"$addFields": {"name": "$_id.name"}},
                {"$unset": "_id"},
                {"$match": {"__aggregation2": {"$gt": 10.0}}},
                {"$project": {"avg_age": "$__aggregation2", "name": 1}},
                {"$sort": SON([("avg_age", 1)])},
            ],
        )

    def test_same_aggregate_in_multiple_annotations(self):
        avg = Avg("age")
        with self.assertNumQueries(1) as ctx:
            list(Author.objects.values("name").annotate(avg_plus_1=avg + 1, avg_plus_2=avg + 2))
        self.assertAggregateQuery(
            ctx.captured_queries[0]["sql"],
            "aggregation__author",
            [
                {
                    "$group": {
                        "__aggregation1": {"$avg": "$age"},
                        "__aggregation2": {"$avg": "$age"},
                        "_id": {"name": "$name"},
                    }
                },
                {"$addFields": {"name": "$_id.name"}},
                {"$unset": "_id"},
                {
                    "$project": {
                        "avg_plus_1": {"$add": ["$__aggregation2", {"$literal": 1}]},
                        "avg_plus_2": {"$add": ["$__aggregation2", {"$literal": 2}]},
                        "name": 1,
                    }
                },
            ],
        )
