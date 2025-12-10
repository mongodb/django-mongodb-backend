from django.db import NotSupportedError
from django.db.models.fields.related_lookups import In, RelatedIn
from django.db.models.lookups import (
    BuiltinLookup,
    FieldGetDbPrepValueIterableMixin,
    IsNull,
    Lookup,
    PatternLookup,
    UUIDTextMixin,
)

from .query_utils import is_constant_value, process_lhs, process_rhs


def builtin_lookup_expr(self, compiler, connection):
    value = process_rhs(self, compiler, connection, as_expr=True)
    lhs_mql = process_lhs(self, compiler, connection, as_expr=True)
    return connection.mongo_expr_operators[self.lookup_name](lhs_mql, value)


def builtin_lookup_path(self, compiler, connection):
    lhs_mql = process_lhs(self, compiler, connection)
    value = process_rhs(self, compiler, connection)
    return connection.mongo_operators[self.lookup_name](lhs_mql, value)


_field_resolve_expression_parameter = FieldGetDbPrepValueIterableMixin.resolve_expression_parameter


def field_resolve_expression_parameter(self, compiler, connection, sql, param):
    """For MongoDB, this method must call as_mql() instead of as_sql()."""
    sql, sql_params = _field_resolve_expression_parameter(self, compiler, connection, sql, param)
    if connection.vendor == "mongodb":
        params = [param]
        if hasattr(param, "resolve_expression"):
            param = param.resolve_expression(compiler.query)
        if hasattr(param, "as_mql"):
            params = [param.as_mql(compiler, connection)]
        return sql, params
    return sql, sql_params


def wrap_in(function):
    def inner(self, compiler, connection):
        db_rhs = getattr(self.rhs, "_db", None)
        if db_rhs is not None and db_rhs != connection.alias:
            raise ValueError(
                "Subqueries aren't allowed across different databases. Force "
                "the inner query to be evaluated using `list(inner_query)`."
            )
        return function(self, compiler, connection)

    return inner


def get_subquery_wrapping_pipeline(self, compiler, connection, field_name, expr):  # noqa: ARG001
    return [
        {
            "$facet": {
                "group": [
                    {
                        "$group": {
                            "_id": None,
                            "tmp_name": {
                                "$addToSet": expr.as_mql(compiler, connection, as_expr=True)
                            },
                        }
                    }
                ]
            }
        },
        {
            "$project": {
                field_name: {
                    "$ifNull": [
                        {
                            "$getField": {
                                "input": {"$arrayElemAt": ["$group", 0]},
                                "field": "tmp_name",
                            }
                        },
                        [],
                    ]
                }
            }
        },
    ]


def is_null_expr(self, compiler, connection):
    if not isinstance(self.rhs, bool):
        raise ValueError("The QuerySet value for an isnull lookup must be True or False.")
    lhs_mql = process_lhs(self, compiler, connection, as_expr=True)
    return connection.mongo_expr_operators["isnull"](lhs_mql, self.rhs)


def is_null_path(self, compiler, connection):
    if not isinstance(self.rhs, bool):
        raise ValueError("The QuerySet value for an isnull lookup must be True or False.")
    lhs_mql = process_lhs(self, compiler, connection)
    return connection.mongo_operators["isnull"](lhs_mql, self.rhs)


# from https://www.pcre.org/current/doc/html/pcre2pattern.html#SEC4
REGEX_MATCH_ESCAPE_CHARS = (
    ("\\", r"\\"),  # general escape character
    ("^", r"\^"),  # start of string
    ({"$literal": "$"}, r"\$"),  # end of string
    (".", r"\."),  # match any character
    ("[", r"\["),  # start character class definition
    ("|", r"\|"),  # start of alternative branch
    ("(", r"\("),  # start group or control verb
    (")", r"\)"),  # end group or control verb
    ("*", r"\*"),  #  0 or more quantifier
    ("+", r"\+"),  #  1 or more quantifier
    ("?", r"\?"),  # 0 or 1 quantifier
    ("{", r"\}"),  # start min/max quantifier
)


@property
def lookup_can_use_path(self):
    # Can use path MQL if the LHS is a column and the RHS is a constant.
    return getattr(self.lhs, "is_simple_column", False) and is_constant_value(self.rhs)


def pattern_lookup_prep_lookup_value(self, value):
    if hasattr(self.rhs, "as_mql"):
        # If value is a column reference, escape $regexMatch special chars.
        # Analogous to PatternLookup.get_rhs_op() / pattern_esc.
        for find, replacement in REGEX_MATCH_ESCAPE_CHARS:
            value = {"$replaceAll": {"input": value, "find": find, "replacement": replacement}}
    else:
        # If value is a literal, remove percent signs added by
        # PatternLookup.process_rhs() for LIKE queries.
        if self.lookup_name in ("startswith", "istartswith"):
            value = value[:-1]
        elif self.lookup_name in ("endswith", "iendswith"):
            value = value[1:]
        elif self.lookup_name in ("contains", "icontains"):
            value = value[1:-1]
    return value


def uuid_text_mixin(self, compiler, connection, as_expr=False):  # noqa: ARG001
    raise NotSupportedError("Pattern lookups on UUIDField are not supported.")


def register_lookups():
    BuiltinLookup.as_mql_expr = builtin_lookup_expr
    BuiltinLookup.as_mql_path = builtin_lookup_path
    FieldGetDbPrepValueIterableMixin.resolve_expression_parameter = (
        field_resolve_expression_parameter
    )
    In.as_mql_expr = RelatedIn.as_mql_expr = wrap_in(builtin_lookup_expr)
    In.as_mql_path = RelatedIn.as_mql_path = wrap_in(builtin_lookup_path)
    In.get_subquery_wrapping_pipeline = get_subquery_wrapping_pipeline
    IsNull.as_mql_expr = is_null_expr
    IsNull.as_mql_path = is_null_path
    Lookup.can_use_path = lookup_can_use_path
    PatternLookup.prep_lookup_value_mongo = pattern_lookup_prep_lookup_value
    UUIDTextMixin.as_mql = uuid_text_mixin
