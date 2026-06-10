from django.db.models.functions import JSONArray

from ..query_utils import process_lhs


def json_array(self, compiler, connection):
    return process_lhs(self, compiler, connection, as_expr=True)


def register_json():
    JSONArray.as_mql_expr = json_array
