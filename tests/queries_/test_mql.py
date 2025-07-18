import json
import re

from bson import ObjectId
from django.db import models
from django.test import TestCase

from .models import Author, Book, Library, Order, Tag


def uglify_mongo_aggregate(query_str):
    """Remove whitespace from a formatted query."""
    # TODO: replace this with a better assertion help, e.g.
    # self.assertQuery("collection", [pipeline])
    m = re.match(r"^(.*?)\((.*)\)$", query_str.strip(), re.DOTALL)
    if not m:
        raise ValueError("String does not match the expected pattern: prefix(...)")
    prefix, inside = m.groups()
    inside = str(json.loads(inside))
    return f"{prefix}({inside})"


class MQLTests(TestCase):
    def test_all(self):
        with self.assertNumQueries(1) as ctx:
            list(Author.objects.all())
        query = ctx.captured_queries[0]["sql"]
        self.assertEqual(query, "db.queries__author.aggregate([{'$match': {'$expr': {}}}])")

    def test_join(self):
        with self.assertNumQueries(1) as ctx:
            list(Book.objects.filter(author__name="Bob"))
        query = ctx.captured_queries[0]["sql"]
        self.assertEqual(
            query,
            "db.queries__book.aggregate(["
            "{'$lookup': {'from': 'queries__author', "
            "'let': {'parent__field__0': '$author_id'}, "
            "'pipeline': [{'$match': {'$expr': "
            "{'$and': [{'$eq': ['$$parent__field__0', '$_id']}, "
            "{'$eq': ['$name', 'Bob']}]}}}], 'as': 'queries__author'}}, "
            "{'$unwind': '$queries__author'}, "
            "{'$match': {'$expr': {'$eq': ['$queries__author.name', 'Bob']}}}])",
        )


class FKLookupConditionPushdownTests(TestCase):
    def test_filter_on_local_and_related_fields(self):
        with self.assertNumQueries(1) as ctx:
            list(Book.objects.filter(title="Don", author__name="John"))
        query = ctx.captured_queries[0]["sql"]
        self.assertEqual(
            query,
            "db.queries__book.aggregate(["
            "{'$lookup': {'from': 'queries__author', "
            "'let': {'parent__field__0': '$author_id'}, 'pipeline': ["
            "{'$match': {'$expr': {'$and': [{'$eq': ['$$parent__field__0', "
            "'$_id']}, {'$eq': ['$name', 'John']}]}}}], 'as': "
            "'queries__author'}}, {'$unwind': '$queries__author'}, {'$match': "
            "{'$expr': {'$and': [{'$eq': ['$queries__author.name', 'John']}, "
            "{'$eq': ['$title', 'Don']}]}}}])",
        )

    def test_or_mixing_local_and_related_fields_is_not_pushable(self):
        with self.assertNumQueries(1) as ctx:
            list(Book.objects.filter(models.Q(title="Don") | models.Q(author__name="John")))
        query = ctx.captured_queries[0]["sql"]
        self.assertEqual(
            query,
            "db.queries__book.aggregate([{'$lookup': {'from': "
            "'queries__author', 'let': {'parent__field__0': '$author_id'}, "
            "'pipeline': [{'$match': {'$expr': {'$and': [{'$eq': "
            "['$$parent__field__0', '$_id']}]}}}], 'as': 'queries__author'}}, "
            "{'$unwind': '$queries__author'}, {'$match': {'$expr': {'$or': "
            "[{'$eq': ['$title', 'Don']}, {'$eq': ['$queries__author.name', "
            "'John']}]}}}])",
        )

    def test_filter_on_self_join_fields(self):
        with self.assertNumQueries(1) as ctx:
            list(
                Tag.objects.filter(
                    parent__name="parent", parent__group_id=ObjectId("6891ff7822e475eddc20f159")
                )
            )
        query = ctx.captured_queries[0]["sql"]
        self.assertEqual(
            query,
            "db.queries__tag.aggregate([{'$lookup': {'from': 'queries__tag', 'let': "
            "{'parent__field__0': '$parent_id'}, 'pipeline': [{'$match': {'$expr': "
            "{'$and': [{'$eq': ['$$parent__field__0', '$_id']}, {'$and': [{'$eq': "
            "['$group_id', ObjectId('6891ff7822e475eddc20f159')]}, {'$eq': ['$name', "
            "'parent']}]}]}}}], 'as': 'T2'}}, {'$unwind': '$T2'}, {'$match': {'$expr': "
            "{'$and': [{'$eq': ['$T2.group_id', ObjectId('6891ff7822e475eddc20f159')]}, "
            "{'$eq': ['$T2.name', 'parent']}]}}}])",
        )

    def test_filter_on_reverse_foreignkey_relation(self):
        with self.assertNumQueries(1) as ctx:
            list(Order.objects.filter(items__status=ObjectId("6891ff7822e475eddc20f159")))
        query = ctx.captured_queries[0]["sql"]
        self.assertEqual(
            query,
            "db.queries__order.aggregate([{'$lookup': {'from': "
            "'queries__orderitem', 'let': {'parent__field__0': '$_id'}, "
            "'pipeline': [{'$match': {'$expr': {'$and': [{'$eq': "
            "['$$parent__field__0', '$order_id']}, {'$eq': ['$status', "
            "ObjectId('6891ff7822e475eddc20f159')]}]}}}], 'as': "
            "'queries__orderitem'}}, {'$unwind': '$queries__orderitem'}, "
            "{'$match': {'$expr': {'$eq': ['$queries__orderitem.status', "
            "ObjectId('6891ff7822e475eddc20f159')]}}}, "
            "{'$addFields': {'_id': '$_id'}}, {'$sort': SON([('_id', 1)])}])",
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
        query = ctx.captured_queries[0]["sql"]
        self.assertEqual(
            query,
            "db.queries__order.aggregate([{'$lookup': {'from': "
            "'queries__orderitem', 'let': {'parent__field__0': '$_id'}, "
            "'pipeline': [{'$match': {'$expr': {'$and': [{'$eq': "
            "['$$parent__field__0', '$order_id']}, {'$eq': ['$status', "
            "ObjectId('6891ff7822e475eddc20f159')]}]}}}], 'as': "
            "'queries__orderitem'}}, {'$unwind': '$queries__orderitem'}, "
            "{'$lookup': {'from': 'queries__order', 'let': "
            "{'parent__field__0': '$queries__orderitem.order_id'}, "
            "'pipeline': [{'$match': {'$expr': {'$and': [{'$eq': "
            "['$$parent__field__0', '$_id']}, {'$eq': ['$name', 'My Order']}]}"
            "}}], 'as': 'T3'}}, {'$unwind': '$T3'}, {'$match': {'$expr': "
            "{'$and': [{'$eq': ['$T3.name', 'My Order']}, {'$eq': "
            "['$queries__orderitem.status', "
            "ObjectId('6891ff7822e475eddc20f159')]}, {'$eq': ['$name', "
            "'My Order']}]}}}, {'$addFields': {'_id': '$_id'}}, "
            "{'$sort': SON([('_id', 1)])}])",
        )

    def test_negated_related_filter_is_not_pushable(self):
        with self.assertNumQueries(1) as ctx:
            list(Book.objects.filter(~models.Q(author__name="John")))
        query = ctx.captured_queries[0]["sql"]
        self.assertEqual(
            query,
            "db.queries__book.aggregate([{'$lookup': {'from': "
            "'queries__author', 'let': {'parent__field__0': '$author_id'}, "
            "'pipeline': [{'$match': {'$expr': {'$and': [{'$eq': "
            "['$$parent__field__0', '$_id']}]}}}], 'as': 'queries__author'}}, "
            "{'$unwind': '$queries__author'}, {'$match': {'$expr': "
            "{'$not': {'$eq': ['$queries__author.name', 'John']}}}}])",
        )

    def test_or_on_local_fields_only(self):
        with self.assertNumQueries(1) as ctx:
            list(Order.objects.filter(models.Q(name="A") | models.Q(name="B")))
        query = ctx.captured_queries[0]["sql"]
        self.assertEqual(
            query,
            "db.queries__order.aggregate([{'$match': {'$expr': {'$or': "
            "[{'$eq': ['$name', 'A']}, {'$eq': ['$name', 'B']}]}}}, "
            "{'$addFields': {'_id': '$_id'}}, {'$sort': SON([('_id', 1)])}])",
        )

    def test_or_with_mixed_pushable_and_non_pushable_fields(self):
        with self.assertNumQueries(1) as ctx:
            list(Book.objects.filter(models.Q(author__name="John") | models.Q(title="Don")))
        query = ctx.captured_queries[0]["sql"]
        self.assertEqual(
            query,
            "db.queries__book.aggregate([{'$lookup': {'from': "
            "'queries__author', 'let': {'parent__field__0': '$author_id'}, "
            "'pipeline': [{'$match': {'$expr': {'$and': [{'$eq': "
            "['$$parent__field__0', '$_id']}]}}}], 'as': 'queries__author'}}, "
            "{'$unwind': '$queries__author'}, {'$match': {'$expr': {'$or': "
            "[{'$eq': ['$queries__author.name', 'John']}, {'$eq': ['$title', "
            "'Don']}]}}}])",
        )

    def test_push_equality_between_parent_and_child_fields(self):
        with self.assertNumQueries(1) as ctx:
            list(Order.objects.filter(items__status=models.F("id")))
        query = ctx.captured_queries[0]["sql"]
        self.assertEqual(
            query,
            "db.queries__order.aggregate([{'$lookup': {'from': 'queries__orderitem', "
            "'let': {'parent__field__0': '$_id', 'parent__field__1': '$_id'}, "
            "'pipeline': [{'$match': {'$expr': {'$and': [{'$eq': "
            "['$$parent__field__0', '$order_id']}, {'$eq': ['$status', "
            "'$$parent__field__1']}]}}}], 'as': 'queries__orderitem'}}, "
            "{'$unwind': '$queries__orderitem'}, {'$match': {'$expr': "
            "{'$eq': ['$queries__orderitem.status', '$_id']}}}, "
            "{'$addFields': {'_id': '$_id'}}, {'$sort': SON([('_id', 1)])}])",
        )


class M2MLookupConditionPushdownTests(TestCase):
    def test_simple_related_filter_is_pushed(self):
        with self.assertNumQueries(1) as ctx:
            list(Library.objects.filter(readers__name="Alice"))
        query = ctx.captured_queries[0]["sql"]
        expected_query = """
            db.queries__library.aggregate([{
                "$lookup": {
                    "from": "queries__library_readers",
                    "let": {
                        "parent__field__0": "$_id"
                    },
                    "pipeline": [{
                        "$match": {
                            "$expr": {
                                "$and": [{
                                    "$eq": [
                                        "$$parent__field__0",
                                        "$library_id"
                                    ]}
                                ]
                            }
                        }
                    }],
                    "as": "queries__library_readers"
                }
            },
            {"$unwind": "$queries__library_readers"},
            {"$lookup": {
                "from": "queries__reader",
                "let": {
                    "parent__field__0": "$queries__library_readers.reader_id"
                },
                "pipeline": [
                    {
                        "$match": {
                            "$expr": {
                                "$and": [
                                    {"$eq": ["$$parent__field__0", "$_id"]},
                                    {"$eq": ["$name", "Alice"]}
                                ]
                            }
                        }
                    }
                ], "as": "queries__reader"
            }},
            {"$unwind": "$queries__reader"},
            {"$match": {"$expr": {"$eq": ["$queries__reader.name", "Alice"]}}}
        ])
        """
        self.assertEqual(query, uglify_mongo_aggregate(expected_query))

    def test_subquery_join_is_pushed(self):
        with self.assertNumQueries(1) as ctx:
            list(Library.objects.filter(~models.Q(readers__name="Alice")))
        query = ctx.captured_queries[0]["sql"]
        expected_query = """
db.queries__library.aggregate([
  {
    "$lookup": {
      "as": "__subquery0",
      "from": "queries__library_readers",
      "let": {"parent__field__0": "$_id"},
      "pipeline": [
        {
          "$lookup": {
            "from": "queries__reader",
            "let": {"parent__field__0": "$reader_id"},
            "pipeline": [
              {
                "$match": {
                  "$expr": {
                    "$and": [
                      {"$eq": ["$$parent__field__0", "$_id"]},
                      {"$eq": ["$name", "Alice"]}
                    ]
                  }
                }
              }
            ],
            "as": "U2"
          }
        },
        {"$unwind": "$U2"},
        {
          "$match": {
            "$expr": {
              "$and": [
                {"$eq": ["$U2.name", "Alice"]},
                {"$eq": ["$library_id","$$parent__field__0"]}
              ]
            }
          }
        },
        {"$project": {"a": {"$literal": 1}}},
        {"$limit": 1}
      ]
    }
  },
  {
    "$set": {
      "__subquery0": {
        "$cond": {
          "if": {
            "$or": [
              {"$eq": [{"$type": "$__subquery0"}, "missing"]},
              {"$eq": [{"$size": "$__subquery0"}, 0]}
            ]
          },
          "then": {},
          "else": {"$arrayElemAt": ["$__subquery0",0]}
        }
      }
    }
  },
  {
    "$match": {
      "$expr": {
        "$not": {
          "$eq": [
            {
              "$not": {
                "$or": [
                  {"$eq": [{"$type": "$__subquery0.a"}, "missing"]},
                  {"$eq": ["$__subquery0.a", null]}
                ]
              }
            },
            true
          ]
        }
      }
    }
  }
])
"""
        self.assertEqual(query, uglify_mongo_aggregate(expected_query))

    def test_filter_on_local_and_related_fields(self):
        with self.assertNumQueries(1) as ctx:
            list(Library.objects.filter(name="Central", readers__name="Alice"))
        query = ctx.captured_queries[0]["sql"]
        expected_query = """
        db.queries__library.aggregate(
[
  {
    "$lookup": {
      "from": "queries__library_readers",
      "let": {"parent__field__0": "$_id"},
      "pipeline": [
        {
          "$match": {
            "$expr": {
              "$and": [{"$eq": ["$$parent__field__0", "$library_id"]}]
            }
          }
        }
      ],
      "as": "queries__library_readers"
    }
  },
  {
    "$unwind": "$queries__library_readers"
  },
  {
    "$lookup": {
      "from": "queries__reader",
      "let": {"parent__field__0": "$queries__library_readers.reader_id"},
      "pipeline": [
        {
          "$match": {
            "$expr": {
              "$and": [
                {"$eq": ["$$parent__field__0", "$_id"]},
                {"$eq": ["$name", "Alice"]}
              ]
            }
          }
        }
      ],
      "as": "queries__reader"
    }
  },
  {"$unwind": "$queries__reader"},
  {
    "$match": {
      "$expr": {
        "$and": [
          {"$eq": ["$name", "Central"]},
          {"$eq": ["$queries__reader.name", "Alice"]}
        ]
      }
    }
  }
]
)
"""
        self.assertEqual(query, uglify_mongo_aggregate(expected_query))

    def test_or_on_local_fields_only(self):
        with self.assertNumQueries(1) as ctx:
            list(
                Library.objects.annotate(foreing_field=models.F("readers__name")).filter(
                    name="Ateneo"
                )
            )
        query = ctx.captured_queries[0]["sql"]
        expected_query = """
        db.queries__library.aggregate(
[
  {
    "$lookup": {
      "from": "queries__library_readers",
      "let": {"parent__field__0": "$_id"},
      "pipeline": [
        {
          "$match": {
            "$expr": {"$and": [{"$eq": ["$$parent__field__0","$library_id"]}]}
          }
        }
      ],
      "as": "queries__library_readers"
    }
  },
  {
    "$set": {
      "queries__library_readers": {
        "$cond": {
          "if": {
            "$or": [
              {"$eq": [{"$type": "$queries__library_readers"}, "missing"]},
              {"$eq": [{"$size": "$queries__library_readers"}, 0]}
            ]
          },
          "then": [{}],
          "else": "$queries__library_readers"
        }
      }
    }
  },
  {"$unwind": "$queries__library_readers"},
  {
    "$lookup": {
      "from": "queries__reader",
      "let": {
        "parent__field__0": "$queries__library_readers.reader_id"
      },
      "pipeline": [
        {
          "$match": {
            "$expr": {"$and": [{"$eq": ["$$parent__field__0", "$_id"]}]}
          }
        }
      ],
      "as": "queries__reader"
    }
  },
  {
    "$set": {
      "queries__reader": {
        "$cond": {
          "if": {
            "$or": [
              {"$eq": [{"$type": "$queries__reader"}, "missing"]},
              {"$eq": [{"$size": "$queries__reader"}, 0]}
            ]
          },
          "then": [{}],
          "else": "$queries__reader"
        }
      }
    }
  },
  {"$unwind": "$queries__reader"},
  {"$match": {"$expr": {"$eq": ["$name", "Ateneo"]}}},
  {
    "$project": {
      "queries__reader": {"foreing_field": "$queries__reader.name"},
      "_id": 1,
      "name": 1
    }
  }
])
"""
        self.assertEqual(query, uglify_mongo_aggregate(expected_query))

    def test_or_with_mixed_pushable_and_non_pushable_fields(self):
        with self.assertNumQueries(1) as ctx:
            list(Library.objects.filter(models.Q(readers__name="Alice") | models.Q(name="Central")))
        query = ctx.captured_queries[0]["sql"]
        expected_query = """
db.queries__library.aggregate([
  {
    "$lookup": {
      "from": "queries__library_readers",
      "let": {"parent__field__0": "$_id"},
      "pipeline": [
        {
          "$match": {
            "$expr": {"$and": [{"$eq": ["$$parent__field__0", "$library_id"]}]
            }
          }
        }
      ],
      "as": "queries__library_readers"
    }
  },
  {
    "$set": {
      "queries__library_readers": {
        "$cond": {
          "if": {
            "$or": [
              {"$eq": [{"$type": "$queries__library_readers"}, "missing"]},
              {"$eq": [{"$size": "$queries__library_readers"}, 0]}
            ]
          },
          "then": [{}],
          "else": "$queries__library_readers"
        }
      }
    }
  },
  {"$unwind": "$queries__library_readers"},
  {
    "$lookup": {
      "from": "queries__reader",
      "let": {"parent__field__0": "$queries__library_readers.reader_id"},
      "pipeline": [
        {
          "$match": {
            "$expr": {"$and": [{"$eq": ["$$parent__field__0", "$_id"]}]}
          }
        }
      ],
      "as": "queries__reader"
    }
  },
  {
    "$set": {
      "queries__reader": {
        "$cond": {
          "if": {
            "$or": [
              {"$eq": [{"$type": "$queries__reader"}, "missing"]},
              {"$eq": [{"$size": "$queries__reader"}, 0]}
            ]
          },
          "then": [{}],
          "else": "$queries__reader"
        }
      }
    }
  },
  {"$unwind": "$queries__reader"},
  {
    "$match": {
      "$expr": {
        "$or": [
          {"$eq": ["$queries__reader.name", "Alice"]},
          {"$eq": ["$name", "Central"]}
        ]
      }
    }
  }
])
"""
        self.assertEqual(query, uglify_mongo_aggregate(expected_query))
