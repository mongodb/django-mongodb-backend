import datetime
from uuid import UUID

from bson import Decimal128
from django.test import SimpleTestCase

from django_mongodb_backend.query_conversion.expression_converters import convert_expression


class ExpressionConversionTestCase(SimpleTestCase):
    CONVERTIBLE_TYPES = {
        "int": 42,
        "float": 3.14,
        "decimal128": Decimal128("3.14"),
        "boolean": True,
        "NoneType": None,
        "string": "string",
        "datetime": datetime.datetime.now(datetime.timezone.utc),
        "duration": datetime.timedelta(days=5, hours=3),
        "uuid": UUID("12345678123456781234567812345678"),
    }

    def assertConversionEqual(self, input, expected):
        result = convert_expression(input)
        self.assertEqual(result, expected)

    def assertNotOptimizable(self, input):
        result = convert_expression(input)
        self.assertIsNone(result)

    def _test_conversion_various_types(self, conversion_test):
        for _type, val in self.CONVERTIBLE_TYPES.items():
            with self.subTest(_type=_type, val=val):
                conversion_test(val)


class TestExpressionConversion(ExpressionConversionTestCase):
    def test_non_dict_expression(self):
        expr = ["$status", "active"]
        self.assertNotOptimizable(expr)

    def test_empty_dict_expression(self):
        expr = {}
        self.assertNotOptimizable(expr)


class TestEqExprConversion(ExpressionConversionTestCase):
    def test_eq_conversion(self):
        expr = {"$eq": ["$status", "active"]}
        expected = {"status": "active"}
        self.assertConversionEqual(expr, expected)

    def test_eq_no_conversion_non_string_field(self):
        expr = {"$eq": [123, "active"]}
        self.assertNotOptimizable(expr)

    def test_eq_no_conversion_dict_value(self):
        expr = {"$eq": ["$status", {"$gt": 5}]}
        self.assertNotOptimizable(expr)

    def _test_eq_conversion_valid_type(self, _type):
        expr = {"$eq": ["$age", _type]}
        expected = {"age": _type}
        self.assertConversionEqual(expr, expected)

    def _test_eq_conversion_valid_array_type(self, _type):
        expr = {"$eq": ["$age", _type]}
        expected = {"age": _type}
        self.assertConversionEqual(expr, expected)

    def test_eq_conversion_various_types(self):
        self._test_conversion_various_types(self._test_eq_conversion_valid_type)

    def test_eq_conversion_various_array_types(self):
        self._test_conversion_various_types(self._test_eq_conversion_valid_array_type)


class TestInExprConversion(ExpressionConversionTestCase):
    def test_in_conversion(self):
        expr = {"$in": ["$category", ["electronics", "books", "clothing"]]}
        expected = {"category": {"$in": ["electronics", "books", "clothing"]}}
        self.assertConversionEqual(expr, expected)

    def test_in_no_conversion_non_string_field(self):
        expr = {"$in": [123, ["electronics", "books"]]}
        self.assertNotOptimizable(expr)

    def test_in_no_conversion_dict_value(self):
        expr = {"$in": ["$status", [{"bad": "val"}]]}
        self.assertNotOptimizable(expr)

    def _test_in_conversion_valid_type(self, _type):
        expr = {
            "$in": [
                "$age",
                [
                    _type,
                ],
            ]
        }
        expected = {
            "age": {
                "$in": [
                    _type,
                ]
            }
        }
        self.assertConversionEqual(expr, expected)

    def test_in_conversion_various_types(self):
        for _type, val in self.CONVERTIBLE_TYPES.items():
            with self.subTest(_type=_type, val=val):
                self._test_in_conversion_valid_type(val)


class TestLogicalExpressionConversion(ExpressionConversionTestCase):
    def test_logical_and_conversion(self):
        expr = {
            "$and": [
                {"$eq": ["$status", "active"]},
                {"$in": ["$category", ["electronics", "books"]]},
                {"$eq": ["$verified", True]},
            ]
        }
        expected = {
            "$and": [
                {"status": "active"},
                {"category": {"$in": ["electronics", "books"]}},
                {"verified": True},
            ]
        }
        self.assertConversionEqual(expr, expected)

    def test_logical_or_conversion(self):
        expr = {
            "$or": [
                {"$eq": ["$status", "active"]},
                {"$in": ["$category", ["electronics", "books"]]},
            ]
        }
        expected = {
            "$or": [
                {"status": "active"},
                {"category": {"$in": ["electronics", "books"]}},
            ]
        }
        self.assertConversionEqual(expr, expected)

    def test_logical_or_conversion_failure(self):
        expr = {
            "$or": [
                {"$eq": ["$status", "active"]},
                {"$in": ["$category", ["electronics", "books"]]},
                {
                    "$and": [
                        {"verified": True},
                        {"$gt": ["$price", "$min_price"]},  # Not optimizable
                    ]
                },
            ]
        }
        self.assertNotOptimizable(expr)

    def test_logical_mixed_conversion(self):
        expr = {
            "$and": [
                {
                    "$or": [
                        {"$eq": ["$status", "active"]},
                        {"$gt": ["$views", 1000]},
                    ]
                },
                {"$in": ["$category", ["electronics", "books"]]},
                {"$eq": ["$verified", True]},
                {"$lte": ["$price", 2000]},
            ]
        }
        expected = {
            "$and": [
                {"$or": [{"status": "active"}, {"views": {"$gt": 1000}}]},
                {"category": {"$in": ["electronics", "books"]}},
                {"verified": True},
                {"price": {"$lte": 2000}},
            ]
        }
        self.assertConversionEqual(expr, expected)


class TestGtExpressionConversion(ExpressionConversionTestCase):
    def test_gt_conversion(self):
        expr = {"$gt": ["$price", 100]}
        expected = {"price": {"$gt": 100}}
        self.assertConversionEqual(expr, expected)

    def test_gt_no_conversion_non_simple_field(self):
        expr = {"$gt": ["$price", "$min_price"]}
        self.assertNotOptimizable(expr)

    def test_gt_no_conversion_dict_value(self):
        expr = {"$gt": ["$price", {}]}
        self.assertNotOptimizable(expr)

    def _test_gt_conversion_valid_type(self, _type):
        expr = {"$gt": ["$price", _type]}
        expected = {"price": {"$gt": _type}}
        self.assertConversionEqual(expr, expected)

    def test_gt_conversion_various_types(self):
        self._test_conversion_various_types(self._test_gt_conversion_valid_type)


class TestGteExpressionConversion(ExpressionConversionTestCase):
    def test_gte_conversion(self):
        expr = {"$gte": ["$price", 100]}
        expected = {"price": {"$gte": 100}}
        self.assertConversionEqual(expr, expected)

    def test_gte_no_conversion_non_simple_field(self):
        expr = {"$gte": ["$price", "$min_price"]}
        self.assertNotOptimizable(expr)

    def test_gte_no_conversion_dict_value(self):
        expr = {"$gte": ["$price", {}]}
        self.assertNotOptimizable(expr)

    def _test_gte_conversion_valid_type(self, _type):
        expr = {"$gte": ["$price", _type]}
        expected = {"price": {"$gte": _type}}
        self.assertConversionEqual(expr, expected)

    def test_gte_conversion_various_types(self):
        self._test_conversion_various_types(self._test_gte_conversion_valid_type)


class TestLtExpressionConversion(ExpressionConversionTestCase):
    def test_lt_conversion(self):
        expr = {"$lt": ["$price", 100]}
        expected = {"price": {"$lt": 100}}
        self.assertConversionEqual(expr, expected)

    def test_lt_no_conversion_non_simple_field(self):
        expr = {"$lt": ["$price", "$min_price"]}
        self.assertNotOptimizable(expr)

    def test_lt_no_conversion_dict_value(self):
        expr = {"$lt": ["$price", {}]}
        self.assertNotOptimizable(expr)

    def _test_lt_conversion_valid_type(self, _type):
        expr = {"$lt": ["$price", _type]}
        expected = {"price": {"$lt": _type}}
        self.assertConversionEqual(expr, expected)

    def test_lt_conversion_various_types(self):
        self._test_conversion_various_types(self._test_lt_conversion_valid_type)


class TestLteExpressionConversion(ExpressionConversionTestCase):
    def test_lte_conversion(self):
        expr = {"$lte": ["$price", 100]}
        expected = {"price": {"$lte": 100}}
        self.assertConversionEqual(expr, expected)

    def test_lte_no_conversion_non_simple_field(self):
        expr = {"$lte": ["$price", "$min_price"]}
        self.assertNotOptimizable(expr)

    def test_lte_no_conversion_dict_value(self):
        expr = {"$lte": ["$price", {}]}
        self.assertNotOptimizable(expr)

    def _test_lte_conversion_valid_type(self, _type):
        expr = {"$lte": ["$price", _type]}
        expected = {"price": {"$lte": _type}}
        self.assertConversionEqual(expr, expected)

    def test_lte_conversion_various_types(self):
        self._test_conversion_various_types(self._test_lte_conversion_valid_type)
