from django.db import connection


class SchemaAssertionMixin:
    def assertAddRemoveIndex(self, editor, model, index):
        with self.assertNumQueries(1):
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
