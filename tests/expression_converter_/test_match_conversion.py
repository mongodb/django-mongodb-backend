from django.test import SimpleTestCase

from django_mongodb_backend.query_conversion.query_optimizer import convert_expr_to_match


class ConvertExprToMatchTests(SimpleTestCase):
    def assertOptimizerEqual(self, input, expected):
        result = convert_expr_to_match(input)
        self.assertEqual(result, expected)

    def test_multiple_optimizable_conditions(self):
        expr = {
            "$expr": {
                "$and": [
                    {"$eq": ["$status", "active"]},
                    {"$in": ["$category", ["electronics", "books"]]},
                    {"$eq": ["$verified", True]},
                    {"$gte": ["$price", 50]},
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
                        {"price": {"$gte": 50}},
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
                    {"$gt": ["$price", "$min_price"]},  # Not optimizable
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
                        {"$expr": {"$gt": ["$price", "$min_price"]}},
                    ],
                }
            }
        ]
        self.assertOptimizerEqual(expr, expected)

    def test_non_optimizable_condition(self):
        expr = {"$expr": {"$gt": ["$price", "$min_price"]}}
        expected = [
            {
                "$match": {
                    "$expr": {"$gt": ["$price", "$min_price"]},
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
                    {"$and": [{"$eq": ["$verified", True]}, {"$lte": ["$price", 50]}]},
                ]
            }
        }
        expected = [
            {
                "$match": {
                    "$or": [
                        {"status": "active"},
                        {"category": {"$in": ["electronics", "books"]}},
                        {"$and": [{"verified": True}, {"price": {"$lte": 50}}]},
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
                        "$or": [
                            {"$eq": ["$status", "active"]},
                            {"$gt": ["$views", 1000]},
                        ]
                    },
                    {"$in": ["$category", ["electronics", "books"]]},
                    {"$eq": ["$verified", True]},
                    {"$gt": ["$price", "$min_price"]},  # Not optimizable
                ]
            }
        }
        expected = [
            {
                "$match": {
                    "$and": [
                        {
                            "$or": [
                                {"status": "active"},
                                {"views": {"$gt": 1000}},
                            ]
                        },
                        {"category": {"$in": ["electronics", "books"]}},
                        {"verified": True},
                        {"$expr": {"$gt": ["$price", "$min_price"]}},
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
                                    {"$eq": ["$type", "$$standard"]},  # Not optimizable
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
