from django.db import connection
from django.db.models import Index


class ConditionalPartialIndex(Index):
    """Mimics django-tasks-db's ConditionalPartialIndex.

    Reports contains_expressions=False so backends still create it.
    """

    @property
    def contains_expressions(self):
        return False


class SchemaAssertionMixin:
    def assertAddRemoveIndex(self, editor, model, index):
        editor.add_index(index=index, model=model)
        try:
            self.assertIn(
                index.name,
                connection.introspection.get_constraints(
                    cursor=None,
                    table_name=model._meta.db_table,
                ),
            )
        finally:
            editor.remove_index(index=index, model=model)
        self.assertNotIn(
            index.name,
            connection.introspection.get_constraints(
                cursor=None,
                table_name=model._meta.db_table,
            ),
        )
