from django.test import SimpleTestCase, TestCase

from django_mongodb_backend.query_conversion.query_optimizer import QueryOptimizer

from .models import Author

optimizer = QueryOptimizer()


class QueryOptimizerTests(SimpleTestCase):
    def assertOptimizerEqual(self, input, expected):
        result = QueryOptimizer().convert_expr_to_match(input)
        self.assertEqual(result, expected)

    def test_multiple_optimizable_conditions(self):
        expr = {
            "$expr": {
                "$and": [
                    {"$eq": ["$status", "active"]},
                    {"$in": ["$category", ["electronics", "books"]]},
                    {"$eq": ["$verified", True]},
                ]
            }
        }
        expected = [
            {
                "$match": {
                    "$and": [
                        {"status": "active"},
                        {"category": {"$in": ["electronics", "books"]}},
                        {"verified": True},
                    ]
                }
            }
        ]
        self.assertOptimizerEqual(expr, expected)

    def test_mixed_optimizable_and_non_optimizable_conditions(self):
        expr = {
            "$expr": {
                "$and": [
                    {"$eq": ["$status", "active"]},
                    {"$gt": ["$price", 100]},  # Not optimizable
                    {"$in": ["$category", ["electronics"]]},
                ]
            }
        }
        expected = [
            {
                "$match": {
                    "$and": [
                        {"status": "active"},
                        {"category": {"$in": ["electronics"]}},
                        {"$expr": {"$gt": ["$price", 100]}},
                    ],
                }
            }
        ]
        self.assertOptimizerEqual(expr, expected)

    def test_non_optimizable_condition(self):
        expr = {"$expr": {"$gt": ["$price", 100]}}
        expected = [
            {
                "$match": {
                    "$expr": {"$gt": ["$price", 100]},
                }
            }
        ]
        self.assertOptimizerEqual(expr, expected)

    def test_nested_logical_conditions(self):
        expr = {
            "$expr": {
                "$or": [
                    {"$eq": ["$status", "active"]},
                    {"$in": ["$category", ["electronics", "books"]]},
                    {"$and": [{"$eq": ["$verified", True]}, {"$gt": ["$price", 50]}]},
                ]
            }
        }
        expected = [
            {
                "$match": {
                    "$or": [
                        {"status": "active"},
                        {"category": {"$in": ["electronics", "books"]}},
                        {
                            "$expr": {
                                "$and": [{"$eq": ["$verified", True]}, {"$gt": ["$price", 50]}]
                            }
                        },
                    ]
                }
            }
        ]
        self.assertOptimizerEqual(expr, expected)

    def test_complex_nested_with_non_optimizable_parts(self):
        expr = {
            "$expr": {
                "$and": [
                    {
                        "$or": [  # Not optimizable because of $gt
                            {"$eq": ["$status", "active"]},
                            {"$gt": ["$views", 1000]},
                        ]
                    },
                    {"$in": ["$category", ["electronics", "books"]]},
                    {"$eq": ["$verified", True]},
                    {"$gt": ["$price", 50]},  # Not optimizable
                ]
            }
        }
        expected = [
            {
                "$match": {
                    "$and": [
                        {"category": {"$in": ["electronics", "books"]}},
                        {"verified": True},
                        {
                            "$expr": {
                                "$or": [
                                    {"$eq": ["$status", "active"]},
                                    {"$gt": ["$views", 1000]},
                                ]
                            }
                        },
                        {"$expr": {"$gt": ["$price", 50]}},
                    ]
                }
            }
        ]
        self.assertOptimizerEqual(expr, expected)

    def test_london_in_case(self):
        expr = {"$expr": {"$in": ["$author_city", ["London"]]}}
        expected = [{"$match": {"author_city": {"$in": ["London"]}}}]
        self.assertOptimizerEqual(expr, expected)

    def test_deeply_nested_logical_operators(self):
        expr = {
            "$expr": {
                "$and": [
                    {
                        "$or": [
                            {"$eq": ["$type", "premium"]},
                            {
                                "$and": [
                                    {"$eq": ["$type", "standard"]},
                                    {"$in": ["$region", ["US", "CA"]]},
                                ]
                            },
                        ]
                    },
                    {"$eq": ["$active", True]},
                ]
            }
        }
        expected = [
            {
                "$match": {
                    "$and": [
                        {
                            "$or": [
                                {"type": "premium"},
                                {
                                    "$and": [
                                        {"type": "standard"},
                                        {"region": {"$in": ["US", "CA"]}},
                                    ]
                                },
                            ]
                        },
                        {"active": True},
                    ]
                }
            }
        ]
        self.assertOptimizerEqual(expr, expected)

    def test_deeply_nested_logical_operator_with_variable(self):
        expr = {
            "$expr": {
                "$and": [
                    {
                        "$or": [
                            {"$eq": ["$type", "premium"]},
                            {
                                "$and": [
                                    # Not optimizable because of Variable
                                    {"$eq": ["$type", "$$standard"]},
                                    {"$in": ["$region", ["US", "CA"]]},
                                ]
                            },
                        ]
                    },
                    {"$eq": ["$active", True]},
                ]
            }
        }
        expected = [
            {
                "$match": {
                    "$and": [
                        {"active": True},
                        {
                            "$expr": {
                                "$or": [
                                    {"$eq": ["$type", "premium"]},
                                    {
                                        "$and": [
                                            {"$eq": ["$type", "$$standard"]},
                                            {"$in": ["$region", ["US", "CA"]]},
                                        ]
                                    },
                                ]
                            }
                        },
                    ]
                }
            }
        ]
        self.assertOptimizerEqual(expr, expected)


class OptimizedMatchMQLTests(TestCase):
    def test_in_query(self):
        with self.assertNumQueries(1) as ctx:
            list(Author.objects.filter(author_city__in=["London"]))
        query = ctx.captured_queries[0]["sql"]
        expected = (
            "db.expression_converter__author.aggregate([{'$match': "
            + "{'author_city': {'$in': ('London',)}}}])"
        )
        self.assertEqual(query, expected)

    def test_eq_query(self):
        with self.assertNumQueries(1) as ctx:
            list(Author.objects.filter(name="Alice"))
        query = ctx.captured_queries[0]["sql"]
        expected = "db.expression_converter__author.aggregate([{'$match': {'name': 'Alice'}}])"
        self.assertEqual(query, expected)

    def test_eq_and_in_query(self):
        with self.assertNumQueries(1) as ctx:
            list(Author.objects.filter(name="Alice", author_city__in=["London", "New York"]))
        query = ctx.captured_queries[0]["sql"]
        expected = (
            "db.expression_converter__author.aggregate([{'$match': {'$and': "
            + "[{'author_city': {'$in': ('London', 'New York')}}, {'name': 'Alice'}]}}])"
        )
        self.assertEqual(query, expected)
