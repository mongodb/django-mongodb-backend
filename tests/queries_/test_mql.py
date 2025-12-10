from bson import SON, ObjectId
from django.db import models
from django.db.models import Case, F, IntegerField, Value, When
from django.test import TestCase

from django_mongodb_backend.test import MongoTestCaseMixin

from .models import Author, Book, Library, Order, Tag


class MQLTests(MongoTestCaseMixin, TestCase):
    def test_all(self):
        with self.assertNumQueries(1) as ctx:
            list(Author.objects.all())
        self.assertAggregateQuery(ctx.captured_queries[0]["sql"], "queries__author", [])

    def test_join(self):
        with self.assertNumQueries(1) as ctx:
            list(Book.objects.filter(author__name="Bob"))
        self.assertAggregateQuery(
            ctx.captured_queries[0]["sql"],
            "queries__book",
            [
                {
                    "$lookup": {
                        "as": "queries__author",
                        "foreignField": "_id",
                        "from": "queries__author",
                        "localField": "author_id",
                        "pipeline": [{"$match": {"name": "Bob"}}],
                    }
                },
                {"$unwind": "$queries__author"},
                {"$match": {"queries__author.name": "Bob"}},
            ],
        )


class FKLookupConditionPushdownTests(MongoTestCaseMixin, TestCase):
    def test_filter_on_local_and_related_fields(self):
        with self.assertNumQueries(1) as ctx:
            list(Book.objects.filter(title="Don", author__name="John"))
        self.assertAggregateQuery(
            ctx.captured_queries[0]["sql"],
            "queries__book",
            [
                {
                    "$lookup": {
                        "from": "queries__author",
                        "pipeline": [{"$match": {"name": "John"}}],
                        "as": "queries__author",
                        "localField": "author_id",
                        "foreignField": "_id",
                    }
                },
                {"$unwind": "$queries__author"},
                {"$match": {"$and": [{"queries__author.name": "John"}, {"title": "Don"}]}},
            ],
        )

    def test_or_mixing_local_and_related_fields_is_not_pushable(self):
        with self.assertNumQueries(1) as ctx:
            list(Book.objects.filter(models.Q(title="Don") | models.Q(author__name="John")))
        self.assertAggregateQuery(
            ctx.captured_queries[0]["sql"],
            "queries__book",
            [
                {
                    "$lookup": {
                        "from": "queries__author",
                        "pipeline": [],
                        "as": "queries__author",
                        "localField": "author_id",
                        "foreignField": "_id",
                    }
                },
                {"$unwind": "$queries__author"},
                {"$match": {"$or": [{"title": "Don"}, {"queries__author.name": "John"}]}},
            ],
        )

    def test_filter_on_self_join_fields(self):
        with self.assertNumQueries(1) as ctx:
            list(
                Tag.objects.filter(
                    parent__name="parent", parent__group_id=ObjectId("6891ff7822e475eddc20f159")
                )
            )
        self.assertAggregateQuery(
            ctx.captured_queries[0]["sql"],
            "queries__tag",
            [
                {
                    "$lookup": {
                        "from": "queries__tag",
                        "pipeline": [
                            {
                                "$match": {
                                    "$and": [
                                        {"group_id": ObjectId("6891ff7822e475eddc20f159")},
                                        {"name": "parent"},
                                    ]
                                }
                            }
                        ],
                        "as": "T2",
                        "localField": "parent_id",
                        "foreignField": "_id",
                    }
                },
                {"$unwind": "$T2"},
                {
                    "$match": {
                        "$and": [
                            {"T2.group_id": ObjectId("6891ff7822e475eddc20f159")},
                            {"T2.name": "parent"},
                        ]
                    }
                },
            ],
        )

    def test_filter_on_reverse_foreignkey_relation(self):
        with self.assertNumQueries(1) as ctx:
            list(Order.objects.filter(items__status=ObjectId("6891ff7822e475eddc20f159")))
        self.assertAggregateQuery(
            ctx.captured_queries[0]["sql"],
            "queries__order",
            [
                {
                    "$lookup": {
                        "from": "queries__orderitem",
                        "localField": "_id",
                        "foreignField": "order_id",
                        "as": "queries__orderitem",
                        "pipeline": [{"$match": {"status": ObjectId("6891ff7822e475eddc20f159")}}],
                    }
                },
                {"$unwind": "$queries__orderitem"},
                {"$match": {"queries__orderitem.status": ObjectId("6891ff7822e475eddc20f159")}},
                {"$addFields": {"_id": "$_id"}},
                {"$sort": SON([("_id", 1)])},
            ],
        )

    def test_filter_on_local_and_nested_join_fields(self):
        with self.assertNumQueries(1) as ctx:
            list(
                Order.objects.filter(
                    name="My Order",
                    items__order__name="My Order",
                    items__status=ObjectId("6891ff7822e475eddc20f159"),
                )
            )
        self.assertAggregateQuery(
            ctx.captured_queries[0]["sql"],
            "queries__order",
            [
                {
                    "$lookup": {
                        "from": "queries__orderitem",
                        "localField": "_id",
                        "foreignField": "order_id",
                        "pipeline": [{"$match": {"status": ObjectId("6891ff7822e475eddc20f159")}}],
                        "as": "queries__orderitem",
                    }
                },
                {"$unwind": "$queries__orderitem"},
                {
                    "$lookup": {
                        "from": "queries__order",
                        "pipeline": [{"$match": {"name": "My Order"}}],
                        "as": "T3",
                        "localField": "queries__orderitem.order_id",
                        "foreignField": "_id",
                    }
                },
                {"$unwind": "$T3"},
                {
                    "$match": {
                        "$and": [
                            {"T3.name": "My Order"},
                            {"queries__orderitem.status": ObjectId("6891ff7822e475eddc20f159")},
                            {"name": "My Order"},
                        ]
                    }
                },
                {"$addFields": {"_id": "$_id"}},
                {"$sort": SON([("_id", 1)])},
            ],
        )

    def test_negated_related_filter_is_pushable(self):
        with self.assertNumQueries(1) as ctx:
            list(Book.objects.filter(~models.Q(author__name="John")))
        self.assertAggregateQuery(
            ctx.captured_queries[0]["sql"],
            "queries__book",
            [
                {
                    "$lookup": {
                        "from": "queries__author",
                        "as": "queries__author",
                        "localField": "author_id",
                        "foreignField": "_id",
                        "pipeline": [
                            {
                                "$match": {
                                    "$nor": [{"name": "John"}],
                                }
                            }
                        ],
                    }
                },
                {"$unwind": "$queries__author"},
                {"$match": {"$nor": [{"queries__author.name": "John"}]}},
            ],
        )

    def test_or_on_local_fields_only(self):
        with self.assertNumQueries(1) as ctx:
            list(Order.objects.filter(models.Q(name="A") | models.Q(name="B")))
        self.assertAggregateQuery(
            ctx.captured_queries[0]["sql"],
            "queries__order",
            [
                {"$match": {"$or": [{"name": "A"}, {"name": "B"}]}},
                {"$addFields": {"_id": "$_id"}},
                {"$sort": SON([("_id", 1)])},
            ],
        )

    def test_or_with_mixed_pushable_and_non_pushable_fields(self):
        with self.assertNumQueries(1) as ctx:
            list(Book.objects.filter(models.Q(author__name="John") | models.Q(title="Don")))
        self.assertAggregateQuery(
            ctx.captured_queries[0]["sql"],
            "queries__book",
            [
                {
                    "$lookup": {
                        "from": "queries__author",
                        "pipeline": [],
                        "as": "queries__author",
                        "localField": "author_id",
                        "foreignField": "_id",
                    }
                },
                {"$unwind": "$queries__author"},
                {"$match": {"$or": [{"queries__author.name": "John"}, {"title": "Don"}]}},
            ],
        )

    def test_push_equality_between_parent_and_child_fields(self):
        with self.assertNumQueries(1) as ctx:
            list(Order.objects.filter(items__status=models.F("id")))
        self.assertAggregateQuery(
            ctx.captured_queries[0]["sql"],
            "queries__order",
            [
                {
                    "$lookup": {
                        "from": "queries__orderitem",
                        "let": {"parent__field__0": "$_id"},
                        "pipeline": [
                            {"$match": {"$expr": {"$eq": ["$status", "$$parent__field__0"]}}}
                        ],
                        "as": "queries__orderitem",
                        "localField": "_id",
                        "foreignField": "order_id",
                    }
                },
                {"$unwind": "$queries__orderitem"},
                {"$match": {"$expr": {"$eq": ["$queries__orderitem.status", "$_id"]}}},
                {"$addFields": {"_id": "$_id"}},
                {"$sort": SON([("_id", 1)])},
            ],
        )

    def test_double_negation_pushdown(self):
        a1 = Author.objects.create(name="Alice")
        a2 = Author.objects.create(name="Bob")
        b1 = Book.objects.create(title="Book1", author=a1, isbn="111")
        Book.objects.create(title="Book2", author=a2, isbn="222")
        b3 = Book.objects.create(title="Book3", author=a1, isbn="333")
        with self.assertNumQueries(1) as ctx:
            self.assertSequenceEqual(
                Book.objects.filter(~(~models.Q(author__name="Alice") | models.Q(title="Book4"))),
                [b1, b3],
            )
        self.assertAggregateQuery(
            ctx.captured_queries[0]["sql"],
            "queries__book",
            [
                {
                    "$lookup": {
                        "from": "queries__author",
                        "pipeline": [{"$match": {"name": "Alice"}}],
                        "as": "queries__author",
                        "localField": "author_id",
                        "foreignField": "_id",
                    }
                },
                {"$unwind": "$queries__author"},
                {
                    "$match": {
                        "$nor": [
                            {
                                "$or": [
                                    {"$nor": [{"queries__author.name": "Alice"}]},
                                    {"title": "Book4"},
                                ]
                            }
                        ]
                    }
                },
            ],
        )

    def test_partial_or_pushdown(self):
        a1 = Author.objects.create(name="Alice")
        a2 = Author.objects.create(name="Bob")
        a3 = Author.objects.create(name="Charlie")
        b1 = Book.objects.create(title="B1", author=a1, isbn="111")
        b2 = Book.objects.create(title="B2", author=a2, isbn="111")
        Book.objects.create(title="B3", author=a3, isbn="222")
        with self.assertNumQueries(1) as ctx:
            self.assertSequenceEqual(
                Book.objects.filter(
                    models.Q(author__name="Alice")
                    | (models.Q(author__name="Bob") & models.Q(isbn="111"))
                ),
                [b1, b2],
            )
        self.assertAggregateQuery(
            ctx.captured_queries[0]["sql"],
            "queries__book",
            [
                {
                    "$lookup": {
                        "from": "queries__author",
                        "pipeline": [{"$match": {"$or": [{"name": "Alice"}, {"name": "Bob"}]}}],
                        "as": "queries__author",
                        "localField": "author_id",
                        "foreignField": "_id",
                    }
                },
                {"$unwind": "$queries__author"},
                {
                    "$match": {
                        "$or": [
                            {"queries__author.name": "Alice"},
                            {"$and": [{"queries__author.name": "Bob"}, {"isbn": "111"}]},
                        ]
                    }
                },
            ],
        )

    def test_multiple_ors_with_partial_pushdown(self):
        a1 = Author.objects.create(name="Alice")
        a2 = Author.objects.create(name="Bob")
        a3 = Author.objects.create(name="Charlie")
        a4 = Author.objects.create(name="David")
        b1 = Book.objects.create(title="B1", author=a1, isbn="111")
        b2 = Book.objects.create(title="B2", author=a1, isbn="222")
        b3 = Book.objects.create(title="B3", author=a2, isbn="333")
        b4 = Book.objects.create(title="B4", author=a3, isbn="333")
        Book.objects.create(title="B5", author=a4, isbn="444")
        with self.assertNumQueries(1) as ctx:
            self.assertSequenceEqual(
                Book.objects.filter(
                    models.Q(author__name="Alice") & (models.Q(isbn="111") | models.Q(isbn="222"))
                    | (models.Q(author__name="Bob") | models.Q(author__name="Charlie"))
                    & models.Q(isbn="333")
                ),
                [b1, b2, b3, b4],
            )
        self.assertAggregateQuery(
            ctx.captured_queries[0]["sql"],
            "queries__book",
            [
                {
                    "$lookup": {
                        "from": "queries__author",
                        "pipeline": [
                            {
                                "$match": {
                                    "$or": [
                                        {"name": "Alice"},
                                        {"$or": [{"name": "Bob"}, {"name": "Charlie"}]},
                                    ]
                                }
                            }
                        ],
                        "as": "queries__author",
                        "localField": "author_id",
                        "foreignField": "_id",
                    }
                },
                {"$unwind": "$queries__author"},
                {
                    "$match": {
                        "$or": [
                            {
                                "$and": [
                                    {"queries__author.name": "Alice"},
                                    {"$or": [{"isbn": "111"}, {"isbn": "222"}]},
                                ]
                            },
                            {
                                "$and": [
                                    {
                                        "$or": [
                                            {"queries__author.name": "Bob"},
                                            {"queries__author.name": "Charlie"},
                                        ]
                                    },
                                    {"isbn": "333"},
                                ]
                            },
                        ]
                    }
                },
            ],
        )

    def test_self_join_tag_three_levels_none_pushable(self):
        t1 = Tag.objects.create(name="T1")
        t2 = Tag.objects.create(name="T2", parent=t1)
        t3 = Tag.objects.create(name="T3", parent=t2)
        Tag.objects.create(name="T4", parent=t3)
        Tag.objects.create(name="T5", parent=t1)
        t6 = Tag.objects.create(name="T6", parent=t2)
        with self.assertNumQueries(1) as ctx:
            self.assertSequenceEqual(
                Tag.objects.filter(
                    models.Q(name="T1")
                    | models.Q(parent__name="T2")
                    | models.Q(parent__parent__name="T3")
                ),
                [t1, t3, t6],
            )
        self.assertAggregateQuery(
            ctx.captured_queries[0]["sql"],
            "queries__tag",
            # Django translates this kind of query into left outer join.
            [
                {
                    "$lookup": {
                        "from": "queries__tag",
                        "pipeline": [],
                        "as": "T2",
                        "localField": "parent_id",
                        "foreignField": "_id",
                    }
                },
                {
                    "$set": {
                        "T2": {
                            "$cond": {
                                "if": {
                                    "$or": [
                                        {"$eq": [{"$type": "$T2"}, "missing"]},
                                        {"$eq": [{"$size": "$T2"}, 0]},
                                    ]
                                },
                                "then": [{}],
                                "else": "$T2",
                            }
                        }
                    }
                },
                {"$unwind": "$T2"},
                {
                    "$lookup": {
                        "from": "queries__tag",
                        "pipeline": [],
                        "as": "T3",
                        "localField": "T2.parent_id",
                        "foreignField": "_id",
                    }
                },
                {
                    "$set": {
                        "T3": {
                            "$cond": {
                                "if": {
                                    "$or": [
                                        {"$eq": [{"$type": "$T3"}, "missing"]},
                                        {"$eq": [{"$size": "$T3"}, 0]},
                                    ]
                                },
                                "then": [{}],
                                "else": "$T3",
                            }
                        }
                    }
                },
                {"$unwind": "$T3"},
                {"$match": {"$or": [{"name": "T1"}, {"T2.name": "T2"}, {"T3.name": "T3"}]}},
            ],
        )

    def test_self_join_tag_three_levels_pushable(self):
        t1 = Tag.objects.create(name="T1")
        t2 = Tag.objects.create(name="T2", parent=t1)
        t3 = Tag.objects.create(name="T3", parent=t2)
        Tag.objects.create(name="T4", parent=t3)
        Tag.objects.create(name="T5", parent=t1)
        Tag.objects.create(name="T6", parent=t2)
        with self.assertNumQueries(1) as ctx:
            self.assertSequenceEqual(
                Tag.objects.filter(name="T1", parent__name="T2", parent__parent__name="T3"),
                [],
            )
        self.assertAggregateQuery(
            ctx.captured_queries[0]["sql"],
            "queries__tag",
            [
                {
                    "$lookup": {
                        "from": "queries__tag",
                        "pipeline": [{"$match": {"name": "T2"}}],
                        "as": "T2",
                        "localField": "parent_id",
                        "foreignField": "_id",
                    }
                },
                {"$unwind": "$T2"},
                {
                    "$lookup": {
                        "from": "queries__tag",
                        "pipeline": [{"$match": {"name": "T3"}}],
                        "as": "T3",
                        "localField": "T2.parent_id",
                        "foreignField": "_id",
                    }
                },
                {"$unwind": "$T3"},
                {"$match": {"$and": [{"name": "T1"}, {"T2.name": "T2"}, {"T3.name": "T3"}]}},
            ],
        )

    def test_partial_and_pushdown(self):
        a1 = Author.objects.create(name="Alice")
        a2 = Author.objects.create(name="Bob")
        b1 = Book.objects.create(title="B1", author=a1, isbn="111")
        Book.objects.create(title="B2", author=a2, isbn="222")
        with self.assertNumQueries(1) as ctx:
            self.assertSequenceEqual(
                Book.objects.filter(models.Q(author__name="Alice") & models.Q(title__contains="B")),
                [b1],
            )
        self.assertAggregateQuery(
            ctx.captured_queries[0]["sql"],
            "queries__book",
            [
                {
                    "$lookup": {
                        "from": "queries__author",
                        "pipeline": [{"$match": {"name": "Alice"}}],
                        "as": "queries__author",
                        "localField": "author_id",
                        "foreignField": "_id",
                    }
                },
                {"$unwind": "$queries__author"},
                {
                    "$match": {
                        "$and": [
                            {"queries__author.name": "Alice"},
                            {"title": {"$regex": "B", "$options": ""}},
                        ]
                    }
                },
            ],
        )

    def test_not_or_demorgan_pushdown(self):
        a1 = Author.objects.create(name="Alice")
        a2 = Author.objects.create(name="Bob")
        b1 = Book.objects.create(title="B1", author=a1, isbn="111")
        Book.objects.create(title="B2", author=a2, isbn="222")
        with self.assertNumQueries(1) as ctx:
            self.assertSequenceEqual(
                Book.objects.filter(~(models.Q(author__name="Bob") | models.Q(isbn="222"))),
                [b1],
            )
        self.assertAggregateQuery(
            ctx.captured_queries[0]["sql"],
            "queries__book",
            [
                {
                    "$lookup": {
                        "from": "queries__author",
                        "pipeline": [{"$match": {"$nor": [{"name": "Bob"}]}}],
                        "as": "queries__author",
                        "localField": "author_id",
                        "foreignField": "_id",
                    }
                },
                {"$unwind": "$queries__author"},
                {"$match": {"$nor": [{"$or": [{"queries__author.name": "Bob"}, {"isbn": "222"}]}]}},
            ],
        )

    def test_or_mixed_local_remote_pushdown(self):
        a1 = Author.objects.create(name="Alice")
        a2 = Author.objects.create(name="Bob")
        b1 = Book.objects.create(title="B1", author=a1, isbn="111")
        b2 = Book.objects.create(title="B2", author=a2, isbn="222")
        with self.assertNumQueries(1) as ctx:
            self.assertSequenceEqual(
                Book.objects.filter(models.Q(title="B1") | models.Q(author__name="Bob")), [b1, b2]
            )
        self.assertAggregateQuery(
            ctx.captured_queries[0]["sql"],
            "queries__book",
            [
                {
                    "$lookup": {
                        "from": "queries__author",
                        "pipeline": [],
                        "as": "queries__author",
                        "localField": "author_id",
                        "foreignField": "_id",
                    }
                },
                {"$unwind": "$queries__author"},
                {"$match": {"$or": [{"title": "B1"}, {"queries__author.name": "Bob"}]}},
            ],
        )

    def test_conditional_expression_not_pushed(self):
        a1 = Author.objects.create(name="Vicente")
        a2 = Author.objects.create(name="Carlos")
        a3 = Author.objects.create(name="Maria")
        Book.objects.create(title="B1", author=a1, isbn="111")
        b2 = Book.objects.create(title="B2", author=a2, isbn="222")
        Book.objects.create(title="B3", author=a3, isbn="333")
        qs = Book.objects.annotate(
            score=Case(
                When(author__name="Vicente", then=Value(2)),
                When(author__name="Carlos", then=Value(4)),
                default=Value(1),
                output_field=IntegerField(),
            )
            + Value(1)
        ).filter(score__gt=3)
        with self.assertNumQueries(1) as ctx:
            self.assertSequenceEqual(qs, [b2])
        self.assertAggregateQuery(
            ctx.captured_queries[0]["sql"],
            "queries__book",
            [
                {
                    "$lookup": {
                        "from": "queries__author",
                        "pipeline": [],
                        "as": "queries__author",
                        "localField": "author_id",
                        "foreignField": "_id",
                    }
                },
                {"$unwind": "$queries__author"},
                {
                    "$match": {
                        "$expr": {
                            "$gt": [
                                {
                                    "$add": [
                                        {
                                            "$switch": {
                                                "branches": [
                                                    {
                                                        "case": {
                                                            "$eq": [
                                                                "$queries__author.name",
                                                                "Vicente",
                                                            ]
                                                        },
                                                        "then": {"$literal": 2},
                                                    },
                                                    {
                                                        "case": {
                                                            "$eq": [
                                                                "$queries__author.name",
                                                                "Carlos",
                                                            ]
                                                        },
                                                        "then": {"$literal": 4},
                                                    },
                                                ],
                                                "default": {"$literal": 1},
                                            }
                                        },
                                        {"$literal": 1},
                                    ]
                                },
                                3,
                            ]
                        }
                    }
                },
                {
                    "$project": {
                        "score": {
                            "$add": [
                                {
                                    "$switch": {
                                        "branches": [
                                            {
                                                "case": {
                                                    "$eq": ["$queries__author.name", "Vicente"]
                                                },
                                                "then": {"$literal": 2},
                                            },
                                            {
                                                "case": {
                                                    "$eq": ["$queries__author.name", "Carlos"]
                                                },
                                                "then": {"$literal": 4},
                                            },
                                        ],
                                        "default": {"$literal": 1},
                                    }
                                },
                                {"$literal": 1},
                            ]
                        },
                        "_id": 1,
                        "title": 1,
                        "author_id": 1,
                        "isbn": 1,
                    }
                },
            ],
        )

    def test_simple_annotation_pushdown(self):
        a1 = Author.objects.create(name="Alice")
        a2 = Author.objects.create(name="Bob")
        b1 = Book.objects.create(title="B1", author=a1, isbn="111")
        Book.objects.create(title="B2", author=a2, isbn="222")
        b3 = Book.objects.create(title="B3", author=a1, isbn="333")
        with self.assertNumQueries(1) as ctx:
            self.assertSequenceEqual(
                Book.objects.annotate(name_length=F("author__name")).filter(name_length="Alice"),
                [b1, b3],
            )
        self.assertAggregateQuery(
            ctx.captured_queries[0]["sql"],
            "queries__book",
            [
                {
                    "$lookup": {
                        "from": "queries__author",
                        "pipeline": [{"$match": {"name": "Alice"}}],
                        "as": "queries__author",
                        "localField": "author_id",
                        "foreignField": "_id",
                    }
                },
                {"$unwind": "$queries__author"},
                {"$match": {"queries__author.name": "Alice"}},
                {
                    "$project": {
                        "queries__author": {"name_length": "$queries__author.name"},
                        "_id": 1,
                        "title": 1,
                        "author_id": 1,
                        "isbn": 1,
                    }
                },
            ],
        )


class M2MLookupConditionPushdownTests(MongoTestCaseMixin, TestCase):
    def test_simple_related_filter_is_pushed(self):
        with self.assertNumQueries(1) as ctx:
            list(Library.objects.filter(readers__name="Alice"))
        self.assertAggregateQuery(
            ctx.captured_queries[0]["sql"],
            "queries__library",
            [
                {
                    "$lookup": {
                        "from": "queries__library_readers",
                        "pipeline": [],
                        "as": "queries__library_readers",
                        "localField": "_id",
                        "foreignField": "library_id",
                    }
                },
                {"$unwind": "$queries__library_readers"},
                {
                    "$lookup": {
                        "from": "queries__reader",
                        "pipeline": [{"$match": {"name": "Alice"}}],
                        "as": "queries__reader",
                        "localField": "queries__library_readers.reader_id",
                        "foreignField": "_id",
                    }
                },
                {"$unwind": "$queries__reader"},
                {"$match": {"queries__reader.name": "Alice"}},
            ],
        )

    def test_subquery_join_is_pushed(self):
        with self.assertNumQueries(1) as ctx:
            list(Library.objects.filter(~models.Q(readers__name="Alice")))
        self.assertAggregateQuery(
            ctx.captured_queries[0]["sql"],
            "queries__library",
            [
                {
                    "$lookup": {
                        "as": "__subquery0",
                        "from": "queries__library_readers",
                        "let": {"parent__field__0": "$_id"},
                        "pipeline": [
                            {
                                "$lookup": {
                                    "as": "U2",
                                    "foreignField": "_id",
                                    "from": "queries__reader",
                                    "localField": "reader_id",
                                    "pipeline": [{"$match": {"name": "Alice"}}],
                                }
                            },
                            {"$unwind": "$U2"},
                            {
                                "$match": {
                                    "$and": [
                                        {"U2.name": "Alice"},
                                        {"$expr": {"$eq": ["$library_id", "$$parent__field__0"]}},
                                    ]
                                }
                            },
                            {"$project": {"a": {"$literal": 1}}},
                            {"$limit": 1},
                        ],
                    }
                },
                {
                    "$set": {
                        "__subquery0": {
                            "$cond": {
                                "if": {
                                    "$or": [
                                        {"$eq": [{"$type": "$__subquery0"}, "missing"]},
                                        {"$eq": [{"$size": "$__subquery0"}, 0]},
                                    ]
                                },
                                "then": {},
                                "else": {"$arrayElemAt": ["$__subquery0", 0]},
                            }
                        }
                    }
                },
                {
                    "$match": {
                        "$nor": [
                            {
                                "$expr": {
                                    "$eq": [
                                        {
                                            "$not": {
                                                "$or": [
                                                    {
                                                        "$eq": [
                                                            {"$type": "$__subquery0.a"},
                                                            "missing",
                                                        ]
                                                    },
                                                    {"$eq": ["$__subquery0.a", None]},
                                                ]
                                            }
                                        },
                                        True,
                                    ]
                                }
                            }
                        ]
                    }
                },
            ],
        )

    def test_filter_on_local_and_related_fields(self):
        with self.assertNumQueries(1) as ctx:
            list(Library.objects.filter(name="Central", readers__name="Alice"))
        self.assertAggregateQuery(
            ctx.captured_queries[0]["sql"],
            "queries__library",
            [
                {
                    "$lookup": {
                        "from": "queries__library_readers",
                        "localField": "_id",
                        "foreignField": "library_id",
                        "pipeline": [],
                        "as": "queries__library_readers",
                    }
                },
                {"$unwind": "$queries__library_readers"},
                {
                    "$lookup": {
                        "from": "queries__reader",
                        "pipeline": [{"$match": {"name": "Alice"}}],
                        "as": "queries__reader",
                        "localField": "queries__library_readers.reader_id",
                        "foreignField": "_id",
                    }
                },
                {"$unwind": "$queries__reader"},
                {"$match": {"$and": [{"name": "Central"}, {"queries__reader.name": "Alice"}]}},
            ],
        )

    def test_annotate_foreign_field(self):
        with self.assertNumQueries(1) as ctx:
            list(
                Library.objects.annotate(foreing_field=models.F("readers__name")).filter(
                    name="Ateneo"
                )
            )
        self.assertAggregateQuery(
            ctx.captured_queries[0]["sql"],
            "queries__library",
            [
                {
                    "$lookup": {
                        "from": "queries__library_readers",
                        "localField": "_id",
                        "foreignField": "library_id",
                        "pipeline": [],
                        "as": "queries__library_readers",
                    }
                },
                {
                    "$set": {
                        "queries__library_readers": {
                            "$cond": {
                                "if": {
                                    "$or": [
                                        {
                                            "$eq": [
                                                {"$type": "$queries__library_readers"},
                                                "missing",
                                            ]
                                        },
                                        {"$eq": [{"$size": "$queries__library_readers"}, 0]},
                                    ]
                                },
                                "then": [{}],
                                "else": "$queries__library_readers",
                            }
                        }
                    }
                },
                {"$unwind": "$queries__library_readers"},
                {
                    "$lookup": {
                        "from": "queries__reader",
                        "pipeline": [],
                        "as": "queries__reader",
                        "localField": "queries__library_readers.reader_id",
                        "foreignField": "_id",
                    }
                },
                {
                    "$set": {
                        "queries__reader": {
                            "$cond": {
                                "if": {
                                    "$or": [
                                        {"$eq": [{"$type": "$queries__reader"}, "missing"]},
                                        {"$eq": [{"$size": "$queries__reader"}, 0]},
                                    ]
                                },
                                "then": [{}],
                                "else": "$queries__reader",
                            }
                        }
                    }
                },
                {"$unwind": "$queries__reader"},
                {"$match": {"name": "Ateneo"}},
                {
                    "$project": {
                        "queries__reader": {"foreing_field": "$queries__reader.name"},
                        "_id": 1,
                        "name": 1,
                    }
                },
            ],
        )

    def test_or_with_mixed_pushable_and_non_pushable_fields(self):
        with self.assertNumQueries(1) as ctx:
            list(Library.objects.filter(models.Q(readers__name="Alice") | models.Q(name="Central")))
        self.assertAggregateQuery(
            ctx.captured_queries[0]["sql"],
            "queries__library",
            [
                {
                    "$lookup": {
                        "from": "queries__library_readers",
                        "localField": "_id",
                        "foreignField": "library_id",
                        "pipeline": [],
                        "as": "queries__library_readers",
                    }
                },
                {
                    "$set": {
                        "queries__library_readers": {
                            "$cond": {
                                "if": {
                                    "$or": [
                                        {
                                            "$eq": [
                                                {"$type": "$queries__library_readers"},
                                                "missing",
                                            ]
                                        },
                                        {"$eq": [{"$size": "$queries__library_readers"}, 0]},
                                    ]
                                },
                                "then": [{}],
                                "else": "$queries__library_readers",
                            }
                        }
                    }
                },
                {"$unwind": "$queries__library_readers"},
                {
                    "$lookup": {
                        "from": "queries__reader",
                        "pipeline": [],
                        "as": "queries__reader",
                        "localField": "queries__library_readers.reader_id",
                        "foreignField": "_id",
                    }
                },
                {
                    "$set": {
                        "queries__reader": {
                            "$cond": {
                                "if": {
                                    "$or": [
                                        {"$eq": [{"$type": "$queries__reader"}, "missing"]},
                                        {"$eq": [{"$size": "$queries__reader"}, 0]},
                                    ]
                                },
                                "then": [{}],
                                "else": "$queries__reader",
                            }
                        }
                    }
                },
                {"$unwind": "$queries__reader"},
                {"$match": {"$or": [{"queries__reader.name": "Alice"}, {"name": "Central"}]}},
            ],
        )
