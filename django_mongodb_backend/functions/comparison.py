from django.db.models.functions.comparison import Cast, NullIf

from ..query_utils import process_lhs


def cast(self, compiler, connection):
    output_type = connection.data_types[self.output_field.get_internal_type()]
    lhs_mql = process_lhs(self, compiler, connection, as_expr=True)[0]
    if max_length := self.output_field.max_length:
        lhs_mql = {"$substrCP": [lhs_mql, 0, max_length]}
    # Skip the conversion for "object" as it doesn't need to be transformed for
    # interpretation by JSONField, which can handle types including int,
    # object, or array.
    if output_type != "object":
        lhs_mql = {"$convert": {"input": lhs_mql, "to": output_type}}
    if decimal_places := getattr(self.output_field, "decimal_places", None):
        lhs_mql = {"$trunc": [lhs_mql, decimal_places]}
    return lhs_mql


def null_if(self, compiler, connection):
    """Return None if expr1==expr2 else expr1."""
    expr1, expr2 = (
        expr.as_mql(compiler, connection, as_expr=True) for expr in self.get_source_expressions()
    )
    return {"$cond": {"if": {"$eq": [expr1, expr2]}, "then": None, "else": expr1}}


def register_comparison():
    Cast.as_mql_expr = cast
    NullIf.as_mql_expr = null_if
