from django.db import NotSupportedError
from django.db.models.expressions import Col, Func, Ref, Value
from django.db.models.fields.json import KeyTransform
from django.db.models.fields.related_lookups import In, RelatedIn
from django.db.models.lookups import (
    BuiltinLookup,
    FieldGetDbPrepValueIterableMixin,
    IsNull,
    PatternLookup,
    UUIDTextMixin,
)

from .query_utils import is_direct_value, process_lhs, process_rhs


def is_constant_value(value):
    from django_mongodb_backend.fields.array import Array  # noqa: PLC0415

    if isinstance(value, Array):
        return all(is_constant_value(e) for e in value.get_source_expressions())

    return is_direct_value(value) or (
        isinstance(value, Func | Value)
        and not (
            value.contains_aggregate
            or value.contains_over_clause
            or value.contains_column_references
            or value.contains_subquery
        )
    )


def is_simple_column(lhs):
    while isinstance(lhs, KeyTransform):
        if "." in lhs.key_name:
            return False
        lhs = lhs.lhs
    col = lhs.source if isinstance(lhs, Ref) else lhs
    # Foreign columns from parent cannot be addressed as single match
    return isinstance(col, Col) and col.alias is not None


def builtin_lookup(self, compiler, connection, as_path=False):
    if is_simple_column(self.lhs) and is_constant_value(self.rhs) and as_path:
        lhs_mql = process_lhs(self, compiler, connection, as_path=True)
        value = process_rhs(self, compiler, connection, as_path=True)
        return connection.mongo_operators_match[self.lookup_name](lhs_mql, value)

    value = process_rhs(self, compiler, connection)
    lhs_mql = process_lhs(self, compiler, connection, as_path=False)
    if as_path:
        return {"$expr": connection.mongo_operators_expr[self.lookup_name](lhs_mql, value)}
    return connection.mongo_operators_expr[self.lookup_name](lhs_mql, value)


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


def in_(self, compiler, connection, **extra):
    db_rhs = getattr(self.rhs, "_db", None)
    if db_rhs is not None and db_rhs != connection.alias:
        raise ValueError(
            "Subqueries aren't allowed across different databases. Force "
            "the inner query to be evaluated using `list(inner_query)`."
        )
    return builtin_lookup(self, compiler, connection, **extra)


def get_subquery_wrapping_pipeline(self, compiler, connection, field_name, expr):  # noqa: ARG001
    return [
        {
            "$facet": {
                "group": [
                    {
                        "$group": {
                            "_id": None,
                            "tmp_name": {"$addToSet": expr.as_mql(compiler, connection)},
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


def is_null(self, compiler, connection, as_path=False):
    if not isinstance(self.rhs, bool):
        raise ValueError("The QuerySet value for an isnull lookup must be True or False.")
    if is_constant_value(self.rhs) and as_path and is_simple_column(self.lhs):
        lhs_mql = process_lhs(self, compiler, connection, as_path=as_path)
        return connection.mongo_operators_match["isnull"](lhs_mql, self.rhs)
    lhs_mql = process_lhs(self, compiler, connection, as_path=False)
    if as_path:
        return {"$expr": connection.mongo_operators_expr["isnull"](lhs_mql, self.rhs)}
    return connection.mongo_operators_expr["isnull"](lhs_mql, self.rhs)


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


def uuid_text_mixin(self, compiler, connection):  # noqa: ARG001
    raise NotSupportedError("Pattern lookups on UUIDField are not supported.")


def register_lookups():
    BuiltinLookup.as_mql = builtin_lookup
    FieldGetDbPrepValueIterableMixin.resolve_expression_parameter = (
        field_resolve_expression_parameter
    )
    In.as_mql = RelatedIn.as_mql = in_
    In.get_subquery_wrapping_pipeline = get_subquery_wrapping_pipeline
    IsNull.as_mql = is_null
    PatternLookup.prep_lookup_value_mongo = pattern_lookup_prep_lookup_value
    UUIDTextMixin.as_mql = uuid_text_mixin
