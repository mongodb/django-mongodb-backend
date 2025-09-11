from django.test import TestCase

from django_mongodb_backend.test import MongoTestCaseMixin

from .models import NullableJSONModel, Tag


class MQLTests(MongoTestCaseMixin, TestCase):
    def test_none_filter_nullable_json(self):
        with self.assertNumQueries(1) as ctx:
            list(NullableJSONModel.objects.filter(value=None))
        self.assertAggregateQuery(
            ctx.captured_queries[0]["sql"],
            "queries__nullablejsonmodel",
            [{"$match": {"$and": [{"$exists": False}, {"value": None}]}}],
        )

    def test_none_filter(self):
        with self.assertNumQueries(1) as ctx:
            list(Tag.objects.filter(name=None))
        self.assertAggregateQuery(
            ctx.captured_queries[0]["sql"],
            "queries__nullablejsonmodel",
            [
                {
                    "$match": {
                        "$or": [
                            {"$and": [{"name": {"$exists": True}}, {"name": None}]},
                            {"$expr": {"$eq": [{"$type": "$name"}, "missing"]}},
                        ]
                    }
                }
            ],
        )
