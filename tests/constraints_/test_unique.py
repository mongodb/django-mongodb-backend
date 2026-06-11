import datetime
from decimal import Decimal

from bson import ObjectId, json_util
from django.db import connection
from django.test import TestCase

from .models import UniqueFields


class UniqueConstraintLookupTests(TestCase):
    def _plan_contains_ixscan(self, plan):
        if not connection.features.is_mongodb_8_0:  # MongoDB 7.0 format.
            try:
                return plan["inputStage"]["stage"] == "IXSCAN"
            except KeyError:
                pass
        return "IXSCAN" in plan["stage"]

    def test_exact_lookup_uses_partial_unique_index(self):
        """
        Unique constraints are created in a way that the query planner will use
        to avoid a collection scan.
        """
        row = UniqueFields.objects.create(
            boolean=True,
            date_value=datetime.date(2024, 1, 1),
            decimal_value=Decimal("12.34"),
            float_value=1.5,
            integer=42,
            object_id=ObjectId("6754ed8e584bc9ceaae3c072"),
            small_int=7,
            text="hello",
        )
        for field_name in (
            "boolean",
            "date_value",
            "decimal_value",
            "float_value",
            "integer",
            "object_id",
            "small_int",
            "text",
        ):
            with self.subTest(field=field_name):
                plan = json_util.loads(
                    UniqueFields.objects.filter(**{field_name: getattr(row, field_name)}).explain()
                )["queryPlanner"]["winningPlan"]
                self.assertTrue(self._plan_contains_ixscan(plan))

    def test_exact_lookup_does_not_use_partial_unique_index(self):
        """
        Unique constraints on array, binData, and object aren't used by the
        query planner.
        """
        row = UniqueFields.objects.create(
            array_value=[1, 2, 3],
            binary=b"xxx",
            data={"a": "b"},
        )
        for field_name in ("array_value", "binary", "data"):
            with self.subTest(field=field_name):
                plan = json_util.loads(
                    UniqueFields.objects.filter(**{field_name: getattr(row, field_name)}).explain()
                )["queryPlanner"]["winningPlan"]
                self.assertFalse(self._plan_contains_ixscan(plan))
