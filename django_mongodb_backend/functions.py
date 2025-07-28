from datetime import datetime

from django.conf import settings
from django.db import NotSupportedError
from django.db.models import DateField, DateTimeField, TimeField
from django.db.models.expressions import Func
from django.db.models.functions import JSONArray
from django.db.models.functions.comparison import Cast, Coalesce, Greatest, Least, NullIf
from django.db.models.functions.datetime import (
    Extract,
    ExtractDay,
    ExtractHour,
    ExtractIsoWeekDay,
    ExtractIsoYear,
    ExtractMinute,
    ExtractMonth,
    ExtractSecond,
    ExtractWeek,
    ExtractWeekDay,
    ExtractYear,
    Now,
    TruncBase,
    TruncDate,
    TruncTime,
)
from django.db.models.functions.math import Ceil, Cot, Degrees, Log, Power, Radians, Random, Round
from django.db.models.functions.text import (
    Concat,
    ConcatPair,
    Left,
    Length,
    Lower,
    LTrim,
    Replace,
    RTrim,
    StrIndex,
    Substr,
    Trim,
    Upper,
)

from .query_utils import process_lhs

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
EXTRACT_OPERATORS = {
    ExtractDay.lookup_name: "dayOfMonth",
    ExtractHour.lookup_name: "hour",
    ExtractIsoWeekDay.lookup_name: "isoDayOfWeek",
    ExtractIsoYear.lookup_name: "isoWeekYear",
    ExtractMinute.lookup_name: "minute",
    ExtractMonth.lookup_name: "month",
    ExtractSecond.lookup_name: "second",
    ExtractWeek.lookup_name: "isoWeek",
    ExtractWeekDay.lookup_name: "dayOfWeek",
    ExtractYear.lookup_name: "year",
}


def cast(self, compiler, connection):
    output_type = connection.data_types[self.output_field.get_internal_type()]
    lhs_mql = process_lhs(self, compiler, connection)[0]
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


def concat(self, compiler, connection):
    return self.get_source_expressions()[0].as_mql(compiler, connection)


def concat_pair(self, compiler, connection):
    # null on either side results in null for expression, wrap with coalesce.
    coalesced = self.coalesce()
    return super(ConcatPair, coalesced).as_mql(compiler, connection)


def cot(self, compiler, connection):
    lhs_mql = process_lhs(self, compiler, connection)
    return {"$divide": [1, {"$tan": lhs_mql}]}


def extract(self, compiler, connection):
    lhs_mql = process_lhs(self, compiler, connection)
    operator = EXTRACT_OPERATORS.get(self.lookup_name)
    if operator is None:
        raise NotSupportedError(f"{self.__class__.__name__} is not supported.")
    if timezone := self.get_tzname():
        lhs_mql = {"date": lhs_mql, "timezone": timezone}
    return {f"${operator}": lhs_mql}


def func(self, compiler, connection):
    lhs_mql = process_lhs(self, compiler, connection)
    if self.function is None:
        raise NotSupportedError(f"{self} may need an as_mql() method.")
    operator = MONGO_OPERATORS.get(self.__class__, self.function.lower())
    return {f"${operator}": lhs_mql}


def left(self, compiler, connection):
    return self.get_substr().as_mql(compiler, connection)


def length(self, compiler, connection):
    # Check for null first since $strLenCP only accepts strings.
    lhs_mql = process_lhs(self, compiler, connection)
    return {"$cond": {"if": {"$eq": [lhs_mql, None]}, "then": None, "else": {"$strLenCP": lhs_mql}}}


def log(self, compiler, connection):
    # This function is usually log(base, num) but on MongoDB it's log(num, base).
    clone = self.copy()
    clone.set_source_expressions(self.get_source_expressions()[::-1])
    return func(clone, compiler, connection)


def now(self, compiler, connection):  # noqa: ARG001
    return "$$NOW"


def null_if(self, compiler, connection):
    """Return None if expr1==expr2 else expr1."""
    expr1, expr2 = (expr.as_mql(compiler, connection) for expr in self.get_source_expressions())
    return {"$cond": {"if": {"$eq": [expr1, expr2]}, "then": None, "else": expr1}}


def preserve_null(operator):
    # If the argument is null, the function should return null, not
    # $toLower/Upper's behavior of returning an empty string.
    def wrapped(self, compiler, connection):
        lhs_mql = process_lhs(self, compiler, connection)
        return {
            "$cond": {
                "if": connection.mongo_operators["isnull"](lhs_mql, True),
                "then": None,
                "else": {f"${operator}": lhs_mql},
            }
        }

    return wrapped


def replace(self, compiler, connection):
    expression, text, replacement = process_lhs(self, compiler, connection)
    return {"$replaceAll": {"input": expression, "find": text, "replacement": replacement}}


def round_(self, compiler, connection):
    # Round needs its own function because it's a special case that inherits
    # from Transform but has two arguments.
    return {"$round": [expr.as_mql(compiler, connection) for expr in self.get_source_expressions()]}


def str_index(self, compiler, connection):
    lhs = process_lhs(self, compiler, connection)
    # StrIndex should be 0-indexed (not found) but it's -1-indexed on MongoDB.
    return {"$add": [{"$indexOfCP": lhs}, 1]}


def substr(self, compiler, connection):
    lhs = process_lhs(self, compiler, connection)
    # The starting index is zero-indexed on MongoDB rather than one-indexed.
    lhs[1] = {"$add": [lhs[1], -1]}
    # If no limit is specified, use the length of the string since $substrCP
    # requires one.
    if len(lhs) == 2:
        lhs.append({"$strLenCP": lhs[0]})
    return {"$substrCP": lhs}


def trim(operator):
    def wrapped(self, compiler, connection):
        lhs = process_lhs(self, compiler, connection)
        return {f"${operator}": {"input": lhs}}

    return wrapped


def trunc(self, compiler, connection):
    lhs_mql = process_lhs(self, compiler, connection)
    lhs_mql = {"date": lhs_mql, "unit": self.kind, "startOfWeek": "mon"}
    if timezone := self.get_tzname():
        lhs_mql["timezone"] = timezone
    return {"$dateTrunc": lhs_mql}


_trunc_convert_value = TruncBase.convert_value


def trunc_convert_value(self, value, expression, connection):
    if connection.vendor == "mongodb":
        # A custom TruncBase.convert_value() for MongoDB.
        if value is None:
            return None
        convert_to_tz = settings.USE_TZ and self.get_tzname() != "UTC"
        if isinstance(self.output_field, DateTimeField):
            if convert_to_tz:
                # Unlike other databases, MongoDB returns the value in UTC,
                # so rather than setting the time zone equal to self.tzinfo,
                # the value must be converted to tzinfo.
                value = value.astimezone(self.tzinfo)
        elif isinstance(value, datetime):
            if isinstance(self.output_field, DateField):
                if convert_to_tz:
                    value = value.astimezone(self.tzinfo)
                # Truncate for Trunc(..., output_field=DateField)
                value = value.date()
            elif isinstance(self.output_field, TimeField):
                if convert_to_tz:
                    value = value.astimezone(self.tzinfo)
                # Truncate for Trunc(..., output_field=TimeField)
                value = value.time()
        return value
    return _trunc_convert_value(self, value, expression, connection)


def trunc_date(self, compiler, connection):
    # Cast to date rather than truncate to date.
    lhs_mql = process_lhs(self, compiler, connection)
    tzname = self.get_tzname()
    if tzname and tzname != "UTC":
        raise NotSupportedError(f"TruncDate with tzinfo ({tzname}) isn't supported on MongoDB.")
    return {
        "$dateFromString": {
            "dateString": {
                "$concat": [
                    {"$dateToString": {"format": "%Y-%m-%d", "date": lhs_mql}},
                    # Dates are stored with time(0, 0), so by replacing any
                    # existing time component with that, the result of
                    # TruncDate can be compared to DateField.
                    "T00:00:00.000",
                ]
            },
        }
    }


def trunc_time(self, compiler, connection):
    tzname = self.get_tzname()
    if tzname and tzname != "UTC":
        raise NotSupportedError(f"TruncTime with tzinfo ({tzname}) isn't supported on MongoDB.")
    lhs_mql = process_lhs(self, compiler, connection)
    return {
        "$dateFromString": {
            "dateString": {
                "$concat": [
                    # Times are stored with date(1, 1, 1)), so by
                    # replacing any existing date component with that, the
                    # result of TruncTime can be compared to TimeField.
                    "0001-01-01T",
                    {"$dateToString": {"format": "%H:%M:%S.%L", "date": lhs_mql}},
                ]
            }
        }
    }


def register_functions():
    Cast.as_mql = cast
    Concat.as_mql = concat
    ConcatPair.as_mql = concat_pair
    Cot.as_mql = cot
    Extract.as_mql = extract
    Func.as_mql = func
    JSONArray.as_mql = process_lhs
    Left.as_mql = left
    Length.as_mql = length
    Log.as_mql = log
    Lower.as_mql = preserve_null("toLower")
    LTrim.as_mql = trim("ltrim")
    Now.as_mql = now
    NullIf.as_mql = null_if
    Replace.as_mql = replace
    Round.as_mql = round_
    RTrim.as_mql = trim("rtrim")
    StrIndex.as_mql = str_index
    Substr.as_mql = substr
    Trim.as_mql = trim("trim")
    TruncBase.as_mql = trunc
    TruncBase.convert_value = trunc_convert_value
    TruncDate.as_mql = trunc_date
    TruncTime.as_mql = trunc_time
    Upper.as_mql = preserve_null("toUpper")
