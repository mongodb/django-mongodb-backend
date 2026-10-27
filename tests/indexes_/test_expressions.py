from unittest import mock

from django.db import connection
from django.db.models import F, Index, Q
from django.db.models.functions import Lower
from django.test import TestCase
from pymongo import ASCENDING, DESCENDING
from pymongo.errors import OperationFailure

from .models import Article, DataHolder
from .test_base import ConditionalPartialIndex, SchemaAssertionMixin


class ExpressionIndexTests(SchemaAssertionMixin, TestCase):
    def get_index_keys(self, index, model=Article):
        with connection.schema_editor() as editor:
            idx = index.get_pymongo_index_model(model, schema_editor=editor)
        self.assertIsNotNone(idx)
        return list(idx.document["key"].items())

    def assertRemoveIndexDrops(self, index, keys):
        # Create the index the way an older backend version could have.
        collection = connection.get_collection(Article._meta.db_table)
        collection.create_index(keys, name=index.name)
        try:
            with connection.schema_editor() as editor:
                editor.remove_index(Article, index)
            self.assertNotIn(
                index.name,
                connection.introspection.get_constraints(
                    cursor=None, table_name=Article._meta.db_table
                ),
            )
            with connection.schema_editor(collect_sql=True, atomic=False) as editor:
                editor.remove_index(Article, index)
            self.assertEqual(
                editor.collected_sql,
                [f"db.{Article._meta.db_table}.drop_index('{index.name}')"],
            )
        finally:
            names = [idx["name"] for idx in collection.list_indexes()]
            if index.name in names:
                collection.drop_index(index.name)

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
        # The index was never created (see the 6.0.5 release notes);
        # RemoveIndex swallows IndexNotFound.
        index = Index(F("number").desc(), name="never_created_idx")
        with connection.schema_editor() as editor:
            editor.remove_index(Article, index)

    def test_remove_index_only_swallows_index_not_found(self):
        # Only IndexNotFound is swallowed; other errors surface.
        index = Index(F("number").desc(), name="propagate_idx")
        with (
            mock.patch(
                "pymongo.collection.Collection.drop_index",
                side_effect=OperationFailure("unexpected failure", 1),
            ),
            connection.schema_editor() as editor,
            self.assertRaises(OperationFailure),
        ):
            editor.remove_index(Article, index)

    def test_remove_field_index_not_found_raises(self):
        # Fields-only indexes are always created by add_index().
        index = Index(fields=["headline"], name="missing_field_idx")
        with (
            connection.schema_editor() as editor,
            self.assertRaises(OperationFailure) as cm,
        ):
            editor.remove_index(Article, index)
        self.assertEqual(cm.exception.code, 27)  # IndexNotFound

    def test_remove_index_collect_sql(self):
        # Collecting migration SQL (sqlmigrate) records the drop: introspection
        # isn't a collected operation.
        index = Index(F("number").desc(), name="collect_sql_idx")
        with connection.schema_editor(collect_sql=True, atomic=False) as editor:
            editor.remove_index(Article, index)
        self.assertEqual(
            editor.collected_sql,
            [f"db.{Article._meta.db_table}.drop_index('{index.name}')"],
        )

    def test_sliced_expression_skipped(self):
        # A sliced F() can't be translated (the slice has no MongoDB
        # index-key equivalent): the index is skipped rather than created
        # on the entire field.
        index = Index(F("headline")[1:5], name="slice_idx")
        with connection.schema_editor() as editor:
            self.assertIsNone(index.get_pymongo_index_model(Article, schema_editor=editor))

    def test_untranslatable_expression_with_condition_skipped(self):
        # An untranslatable expression skips the index without raising,
        # even when the condition is untranslatable too.
        index = Index(
            Lower("headline"), name="lower_condition_idx", condition=Q(number__isnull=True)
        )
        with connection.schema_editor() as editor:
            self.assertIsNone(index.get_pymongo_index_model(Article, schema_editor=editor))
            editor.add_index(Article, index)
            editor.remove_index(Article, index)

    def test_remove_index_with_unsupported_condition(self):
        # Removal doesn't translate the partial-filter condition: the index
        # is dropped by name even if its condition can't be translated.
        index = Index("headline", name="unsupported_cond_idx", condition=Q(number__isnull=True))
        self.assertRemoveIndexDrops(index, [("headline", ASCENDING)])

    def test_remove_expression_index_with_unsupported_condition(self):
        # Same as above, for an index with translatable expressions plus an
        # untranslatable condition: removing doesn't rebuild the filter.
        index = Index(
            F("number").desc(), name="expr_unsupported_cond_idx", condition=Q(number__isnull=True)
        )
        self.assertRemoveIndexDrops(index, [("number", DESCENDING)])

    def test_nulls_ordering_skipped(self):
        # MongoDB index keys can't express NULLS LAST.
        index = Index(F("number").desc(nulls_last=True), name="nulls_idx")
        with connection.schema_editor() as editor:
            self.assertIsNone(index.get_pymongo_index_model(Article, schema_editor=editor))

    def test_contains_expressions_false(self):
        # django-tasks-db's ConditionalPartialIndex and similar subclasses
        # report contains_expressions=False so backends still create them.
        index = ConditionalPartialIndex(F("number").desc(), name="conditional_idx")
        self.assertEqual(self.get_index_keys(index), [("number", DESCENDING)])
        with connection.schema_editor() as editor:
            self.assertAddRemoveIndex(editor, Article, index)

    def test_contains_expressions_false_with_untranslatable_expression(self):
        # Even overriding contains_expressions can't force creation of an
        # index with untranslatable expressions.
        index = ConditionalPartialIndex(Lower("headline"), name="conditional_lower_idx")
        with connection.schema_editor() as editor:
            self.assertIsNone(index.get_pymongo_index_model(Article, schema_editor=editor))

    def test_embedded_field_expression(self):
        # F() on a dotted embedded-model path indexes the subfield.
        index = Index(F("data.integer").desc(), name="embedded_expr_idx")
        self.assertEqual(self.get_index_keys(index, DataHolder), [("data.integer", DESCENDING)])
        with connection.schema_editor() as editor:
            self.assertAddRemoveIndex(editor, DataHolder, index)
