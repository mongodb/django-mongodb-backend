import operator

from django.db import NotSupportedError, connection
from django.db.models import Index, Q
from django.test import TestCase

from .models import Article
from .test_base import SchemaAssertionMixin


class PartialIndexTests(SchemaAssertionMixin, TestCase):
    def test_not_supported(self):
        msg = "MongoDB does not support the 'isnull' lookup in indexes."
        with connection.schema_editor() as editor, self.assertRaisesMessage(NotSupportedError, msg):
            Index(
                name="test",
                fields=["headline"],
                condition=Q(pk__isnull=True),
            )._get_condition_mql(Article, schema_editor=editor)

    def test_negated_not_supported(self):
        msg = "MongoDB does not support the '~' operator in indexes."
        with self.assertRaisesMessage(NotSupportedError, msg), connection.schema_editor() as editor:
            Index(
                name="test",
                fields=["headline"],
                condition=~Q(pk__isnull=True),
            )._get_condition_mql(Article, schema_editor=editor)

    def test_xor_not_supported(self):
        msg = "MongoDB does not support the '^' operator lookup in indexes."
        with self.assertRaisesMessage(NotSupportedError, msg), connection.schema_editor() as editor:
            Index(
                name="test",
                fields=["headline"],
                condition=Q(pk__isnull=True) ^ Q(pk__isnull=False),
            )._get_condition_mql(Article, schema_editor=editor)

    def test_operations(self):
        operators = (
            ("gt", "$gt"),
            ("gte", "$gte"),
            ("lt", "$lt"),
            ("lte", "$lte"),
        )
        for op, mongo_operator in operators:
            with self.subTest(operator=op), connection.schema_editor() as editor:
                index = Index(
                    name="test",
                    fields=["headline"],
                    condition=Q(**{f"number__{op}": 3}),
                )
                self.assertEqual(
                    {"number": {mongo_operator: 3}},
                    index._get_condition_mql(Article, schema_editor=editor),
                )
                self.assertAddRemoveIndex(editor, Article, index)

    def test_composite_index(self):
        with connection.schema_editor() as editor:
            index = Index(
                name="test",
                fields=["headline"],
                condition=Q(number__gte=3) & (Q(body__gt="test1") | Q(body__in=["A", "B"])),
            )
            self.assertEqual(
                index._get_condition_mql(Article, schema_editor=editor),
                {
                    "$and": [
                        {"number": {"$gte": 3}},
                        {"$or": [{"body": {"$gt": "test1"}}, {"body": {"$in": ("A", "B")}}]},
                    ]
                },
            )
            self.assertAddRemoveIndex(editor, Article, index)

    def test_composite_op_index(self):
        operators = (
            (operator.or_, "$or"),
            (operator.and_, "$and"),
        )
        for op, mongo_operator in operators:
            with self.subTest(operator=op), connection.schema_editor() as editor:
                index = Index(
                    name="test",
                    fields=["headline"],
                    condition=op(Q(number__gte=3), Q(body__gt="test1")),
                )
                self.assertEqual(
                    {mongo_operator: [{"number": {"$gte": 3}}, {"body": {"$gt": "test1"}}]},
                    index._get_condition_mql(Article, schema_editor=editor),
                )
                self.assertAddRemoveIndex(editor, Article, index)
