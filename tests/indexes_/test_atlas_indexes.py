from django.db import connection
from django.test import TransactionTestCase
from django.test.utils import override_settings

from django_mongodb_backend.indexes import AtlasSearchIndex

from .models import Article


@override_settings(USE_TZ=True)
class PartialIndexTests(TransactionTestCase):
    # Schema editor is used to  create the index to test that it works.
    # available_apps = ["indexes"]
    available_apps = None

    def test_partial_index(self):
        with connection.schema_editor() as editor:
            index = AtlasSearchIndex(
                name="recent_article_idx",
                fields=["number"],
            )
            editor.add_index(index=index, model=Article)
            # with connection.cursor() as cursor:
            #     self.assertIn(
            #         index.name,
            #         connection.introspection.get_constraints(
            #             cursor=cursor,
            #             table_name=Article._meta.db_table,
            #         ),
            #     )
            editor.remove_index(index=index, model=Article)
