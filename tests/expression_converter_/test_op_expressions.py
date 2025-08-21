import datetime
from uuid import UUID

from bson import Decimal128
from django.test import SimpleTestCase

from django_mongodb_backend.query_conversion.expression_converters import convert_expression


class ConversionTestCase(SimpleTestCase):
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


class ExpressionTests(ConversionTestCase):
    def test_non_dict(self):
        self.assertNotOptimizable(["$status", "active"])

    def test_empty_dict(self):
        self.assertNotOptimizable({})


class EqTests(ConversionTestCase):
    def test_conversion(self):
        self.assertConversionEqual({"$eq": ["$status", "active"]}, {"status": "active"})

    def test_no_conversion_non_string_field(self):
        self.assertNotOptimizable({"$eq": [123, "active"]})

    def test_no_conversion_dict_value(self):
        self.assertNotOptimizable({"$eq": ["$status", {"$gt": 5}]})

    def _test_conversion_valid_type(self, _type):
        self.assertConversionEqual({"$eq": ["$age", _type]}, {"age": _type})

    def _test_conversion_valid_array_type(self, _type):
        self.assertConversionEqual({"$eq": ["$age", _type]}, {"age": _type})

    def test_conversion_various_types(self):
        self._test_conversion_various_types(self._test_conversion_valid_type)

    def test_conversion_various_array_types(self):
        self._test_conversion_various_types(self._test_conversion_valid_array_type)


class InTests(ConversionTestCase):
    def test_conversion(self):
        expr = {"$in": ["$category", ["electronics", "books", "clothing"]]}
        expected = {"category": {"$in": ["electronics", "books", "clothing"]}}
        self.assertConversionEqual(expr, expected)

    def test_no_conversion_non_string_field(self):
        self.assertNotOptimizable({"$in": [123, ["electronics", "books"]]})

    def test_no_conversion_dict_value(self):
        self.assertNotOptimizable({"$in": ["$status", [{"bad": "val"}]]})

    def _test_conversion_valid_type(self, _type):
        self.assertConversionEqual({"$in": ["$age", [_type]]}, {"age": {"$in": [_type]}})

    def test_conversion_various_types(self):
        for _type, val in self.CONVERTIBLE_TYPES.items():
            with self.subTest(_type=_type, val=val):
                self._test_conversion_valid_type(val)


class LogicalTests(ConversionTestCase):
    def test_and(self):
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

    def test_or(self):
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

    def test_or_failure(self):
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

    def test_mixed(self):
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


class GtTests(ConversionTestCase):
    def test_conversion(self):
        self.assertConversionEqual({"$gt": ["$price", 100]}, {"price": {"$gt": 100}})

    def test_no_conversion_non_simple_field(self):
        self.assertNotOptimizable({"$gt": ["$price", "$min_price"]})

    def test_no_conversion_dict_value(self):
        self.assertNotOptimizable({"$gt": ["$price", {}]})

    def _test_conversion_valid_type(self, _type):
        self.assertConversionEqual({"$gt": ["$price", _type]}, {"price": {"$gt": _type}})

    def test_conversion_various_types(self):
        self._test_conversion_various_types(self._test_conversion_valid_type)


class GteTests(ConversionTestCase):
    def test_conversion(self):
        expr = {"$gte": ["$price", 100]}
        expected = {"price": {"$gte": 100}}
        self.assertConversionEqual(expr, expected)

    def test_no_conversion_non_simple_field(self):
        expr = {"$gte": ["$price", "$min_price"]}
        self.assertNotOptimizable(expr)

    def test_no_conversion_dict_value(self):
        expr = {"$gte": ["$price", {}]}
        self.assertNotOptimizable(expr)

    def _test_conversion_valid_type(self, _type):
        expr = {"$gte": ["$price", _type]}
        expected = {"price": {"$gte": _type}}
        self.assertConversionEqual(expr, expected)

    def test_conversion_various_types(self):
        self._test_conversion_various_types(self._test_conversion_valid_type)


class LtTests(ConversionTestCase):
    def test_conversion(self):
        self.assertConversionEqual({"$lt": ["$price", 100]}, {"price": {"$lt": 100}})

    def test_no_conversion_non_simple_field(self):
        self.assertNotOptimizable({"$lt": ["$price", "$min_price"]})

    def test_no_conversion_dict_value(self):
        self.assertNotOptimizable({"$lt": ["$price", {}]})

    def _test_conversion_valid_type(self, _type):
        self.assertConversionEqual({"$lt": ["$price", _type]}, {"price": {"$lt": _type}})

    def test_conversion_various_types(self):
        self._test_conversion_various_types(self._test_conversion_valid_type)


class LteTests(ConversionTestCase):
    def test_conversion(self):
        self.assertConversionEqual({"$lte": ["$price", 100]}, {"price": {"$lte": 100}})

    def test_no_conversion_non_simple_field(self):
        self.assertNotOptimizable({"$lte": ["$price", "$min_price"]})

    def test_no_conversion_dict_value(self):
        self.assertNotOptimizable({"$lte": ["$price", {}]})

    def _test_conversion_valid_type(self, _type):
        self.assertConversionEqual({"$lte": ["$price", _type]}, {"price": {"$lte": _type}})

    def test_conversion_various_types(self):
        self._test_conversion_various_types(self._test_conversion_valid_type)
