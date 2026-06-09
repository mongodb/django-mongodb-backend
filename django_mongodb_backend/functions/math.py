from django.db.models.functions.math import Cot, Log, Round, Sign

from ..query_utils import process_lhs
from .base import func


def cot(self, compiler, connection):
    lhs_mql = process_lhs(self, compiler, connection, as_expr=True)
    return {"$divide": [1, {"$tan": lhs_mql}]}


def log(self, compiler, connection):
    # This function is usually log(base, num) but MongoDB uses log(num, base).
    clone = self.copy()
    clone.set_source_expressions(self.get_source_expressions()[::-1])
    return func(clone, compiler, connection)


def round_(self, compiler, connection):
    # Round needs its own function because it's a special case that inherits
    # from Transform but has two arguments.
    return {
        "$round": [
            expr.as_mql(compiler, connection, as_expr=True)
            for expr in self.get_source_expressions()
        ]
    }


def sign(self, compiler, connection):
    lhs_mql = process_lhs(self, compiler, connection, as_expr=True)
    return {
        "$cond": {
            "if": {"$eq": [lhs_mql, None]},
            "then": None,  # Return null for null input.
            "else": {
                "$cond": {
                    "if": {"$eq": [lhs_mql, 0]},
                    "then": 0,  # Return zero for zero input.
                    "else": {"$cmp": [lhs_mql, 0]},  # Otherwise, +1 or -1.
                },
            },
        }
    }


def register_math():
    Cot.as_mql_expr = cot
    Log.as_mql_expr = log
    Round.as_mql_expr = round_
    Sign.as_mql_expr = sign
