from django.db import NotSupportedError
from django.db.models.expressions import Func
from django.db.models.functions.comparison import Coalesce, Greatest, Least
from django.db.models.functions.math import Ceil, Degrees, Power, Radians, Random

from ..query_utils import process_lhs

MONGO_OPERATORS = {
    Ceil: "ceil",
    Coalesce: "ifNull",
    Degrees: "radiansToDegrees",
    Greatest: "max",
    Least: "min",
    Power: "pow",
    Radians: "degreesToRadians",
    Random: "rand",
}


def func(self, compiler, connection):
    lhs_mql = process_lhs(self, compiler, connection, as_expr=True)
    if self.function is None:
        raise NotSupportedError(f"{self.__class__.__name__} may need an as_mql() method.")
    operator = MONGO_OPERATORS.get(self.__class__, self.function.lower())
    return {f"${operator}": lhs_mql}


def register_base():
    Func.as_mql_expr = func
    Func.can_use_path = False
