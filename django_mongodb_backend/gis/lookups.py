from django.contrib.gis.db.models.lookups import DistanceLookupFromFunction, GISLookup
from django.db import NotSupportedError

from django_mongodb_backend.query_utils import process_lhs, process_rhs


def _gis_lookup(self, compiler, connection, as_expr=False):
    lhs_mql = process_lhs(self, compiler, connection, as_expr=as_expr)
    rhs_mql = process_rhs(self, compiler, connection, as_expr=as_expr)
    try:
        rhs_op = self.get_rhs_op(connection, rhs_mql)
    except KeyError as e:
        raise NotSupportedError(f"MongoDB does not support the '{self.lookup_name}' lookup.") from e
    return rhs_op.as_mql(lhs_mql, rhs_mql, self.rhs_params)


def register_lookups():
    GISLookup.as_mql = _gis_lookup
    DistanceLookupFromFunction.as_mql = _gis_lookup
