from django.db import connection
from django.db.models import F, Index, Q
from django.db.models.functions import Lower
from django.test import TestCase
from pymongo import ASCENDING, DESCENDING

from .models import Article, DataHolder
from .test_base import SchemaAssertionMixin


class ExpressionIndexTests(SchemaAssertionMixin, TestCase):
    def get_index_keys(self, index, model=Article):
        with connection.schema_editor() as editor:
            idx = index.get_pymongo_index_model(model, schema_editor=editor)
        self.assertIsNotNone(idx)
        return list(idx.document["key"].items())

    def test_descending_expression(self):
        index = Index(F("number").desc(), name="ordering_desc_idx")
        self.assertEqual(self.get_index_keys(index), [("number", DESCENDING)])
        with connection.schema_editor() as editor:
            self.assertAddRemoveIndex(editor, Article, index)

    def test_mixed_direction_compound(self):
        # A string field name is shorthand for an ascending F().
        index = Index("headline", F("number").desc(), name="ordering_mixed_idx")
        self.assertEqual(
            self.get_index_keys(index),
            [("headline", ASCENDING), ("number", DESCENDING)],
        )
        with connection.schema_editor() as editor:
            self.assertAddRemoveIndex(editor, Article, index)

    def test_expression_with_condition(self):
        # The django-tasks-db use case: ordered keys plus a partial filter.
        index = Index(
            F("number").desc(),
            name="ordering_partial_idx",
            condition=Q(headline="ready"),
        )
        with connection.schema_editor() as editor:
            idx = index.get_pymongo_index_model(Article, schema_editor=editor)
            self.assertEqual(list(idx.document["key"].items()), [("number", DESCENDING)])
            self.assertEqual(
                idx.document["partialFilterExpression"], {"headline": {"$eq": "ready"}}
            )
            self.assertAddRemoveIndex(editor, Article, index)

    def test_untranslatable_expression_skipped(self):
        index = Index(Lower("headline"), name="lower_idx")
        with connection.schema_editor() as editor:
            self.assertIsNone(index.get_pymongo_index_model(Article, schema_editor=editor))
            # add_index()/remove_index() skip the index without raising.
            editor.add_index(Article, index)
            self.assertNotIn(
                index.name,
                connection.introspection.get_constraints(
                    cursor=None, table_name=Article._meta.db_table
                ),
            )
            editor.remove_index(Article, index)

    def test_remove_index_never_created(self):
        # AddIndex ran under a backend version that skipped expression
        # indexes (see the 6.1.1 release notes); RemoveIndex is a no-op.
        index = Index(F("number").desc(), name="never_created_idx")
        with connection.schema_editor() as editor:
            editor.remove_index(Article, index)
            self.assertNotIn(
                index.name,
                connection.introspection.get_constraints(
                    cursor=None, table_name=Article._meta.db_table
                ),
            )

    def test_nulls_ordering_skipped(self):
        # MongoDB index keys can't express NULLS LAST.
        index = Index(F("number").desc(nulls_last=True), name="nulls_idx")
        with connection.schema_editor() as editor:
            self.assertIsNone(index.get_pymongo_index_model(Article, schema_editor=editor))

    def test_contains_expressions_false(self):
        # Some Index subclasses (e.g. django-tasks-db's
        # ConditionalPartialIndex) report contains_expressions=False so that
        # backends which under-report expression support still create the
        # index.
        class ConditionalPartialIndex(Index):
            @property
            def contains_expressions(self):
                return False

        index = ConditionalPartialIndex(F("number").desc(), name="conditional_idx")
        self.assertEqual(self.get_index_keys(index), [("number", DESCENDING)])
        with connection.schema_editor() as editor:
            self.assertAddRemoveIndex(editor, Article, index)

    def test_contains_expressions_false_with_untranslatable_expression(self):
        # Even overriding contains_expressions can't force creation of an
        # index with untranslatable expressions.
        class ConditionalPartialIndex(Index):
            @property
            def contains_expressions(self):
                return False

        index = ConditionalPartialIndex(Lower("headline"), name="conditional_lower_idx")
        with connection.schema_editor() as editor:
            self.assertIsNone(index.get_pymongo_index_model(Article, schema_editor=editor))

    def test_embedded_field_expression(self):
        # F() on a dotted embedded-model path indexes the subfield.
        index = Index(F("data.integer").desc(), name="embedded_expr_idx")
        self.assertEqual(self.get_index_keys(index, DataHolder), [("data.integer", DESCENDING)])
        with connection.schema_editor() as editor:
            self.assertAddRemoveIndex(editor, DataHolder, index)
