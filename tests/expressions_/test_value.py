import datetime
import uuid
from decimal import Decimal

from bson import Decimal128
from django.db.models import Value
from django.test import SimpleTestCase


class ValueTests(SimpleTestCase):
    def test_date(self):
        self.assertEqual(
            Value(datetime.date(2025, 1, 1)).as_mql(None, None),
            datetime.datetime(2025, 1, 1),
        )

    def test_datetime(self):
        self.assertEqual(
            Value(datetime.datetime(2025, 1, 1, 9, 8, 7)).as_mql(None, None),
            datetime.datetime(2025, 1, 1, 9, 8, 7),
        )

    def test_decimal(self):
        self.assertEqual(Value(Decimal("1.0")).as_mql(None, None), Decimal128("1.0"))

    def test_list(self):
        self.assertEqual(Value([1, 2]).as_mql(None, None), {"$literal": [1, 2]})

    def test_time(self):
        self.assertEqual(
            Value(datetime.time(9, 8, 7)).as_mql(None, None),
            datetime.datetime(1, 1, 1, 9, 8, 7),
        )

    def test_timedelta(self):
        self.assertEqual(Value(datetime.timedelta(3600)).as_mql(None, None), 311040000000.0)

    def test_int(self):
        self.assertEqual(Value(1).as_mql(None, None), {"$literal": 1})

    def test_str(self):
        self.assertEqual(Value("foo").as_mql(None, None), "foo")

    def test_uuid(self):
        value = uuid.UUID(int=1)
        self.assertEqual(Value(value).as_mql(None, None), "00000000000000000000000000000001")
