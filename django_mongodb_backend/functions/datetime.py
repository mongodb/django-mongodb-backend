from datetime import datetime

from django.conf import settings
from django.db import NotSupportedError
from django.db.models import DateField, DateTimeField, TimeField
from django.db.models.functions.datetime import (
    Extract,
    ExtractDay,
    ExtractHour,
    ExtractIsoWeekDay,
    ExtractIsoYear,
    ExtractMinute,
    ExtractMonth,
    ExtractQuarter,
    ExtractSecond,
    ExtractWeek,
    ExtractWeekDay,
    ExtractYear,
    Now,
    TruncBase,
    TruncDate,
    TruncTime,
)

from ..query_utils import process_lhs

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


def _get_extract_timezone(self):
    tzname = self.get_tzname()
    # Django formats fixed offset zones as "UTC+HH:MM" but MongoDB only accepts
    # the bare offset form "+HH:MM" / "-HH:MM".
    if tzname and tzname.startswith(("UTC+", "UTC-")):
        return tzname[3:]
    return tzname


def extract(self, compiler, connection):
    lhs_mql = process_lhs(self, compiler, connection, as_expr=True)
    # ExtractQuarter lacks a built-in operator.
    if self.lookup_name == "quarter":
        return extract_quarter(self, compiler, connection)
    operator = EXTRACT_OPERATORS.get(self.lookup_name)
    if operator is None:
        raise NotSupportedError(f"{self.__class__.__name__} is not supported.")
    if timezone := _get_extract_timezone(self):
        lhs_mql = {"date": lhs_mql, "timezone": timezone}
    return {f"${operator}": lhs_mql}


def extract_quarter(self, compiler, connection):
    lhs_mql = process_lhs(self, compiler, connection, as_expr=True)
    if timezone := _get_extract_timezone(self):
        lhs_mql = {"date": lhs_mql, "timezone": timezone}
    return {"$ceil": {"$divide": [{"$month": lhs_mql}, 3]}}


def now(self, compiler, connection):  # noqa: ARG001
    return "$$NOW"


def trunc(self, compiler, connection):
    lhs_mql = process_lhs(self, compiler, connection, as_expr=True)
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
    lhs_mql = process_lhs(self, compiler, connection, as_expr=True)
    date_to_string = {"format": "%Y-%m-%d", "date": lhs_mql}
    if tzname := self.get_tzname():
        date_to_string["timezone"] = tzname
    return {
        "$dateFromString": {
            "dateString": {
                "$concat": [
                    {"$dateToString": date_to_string},
                    # Dates are stored with time(0, 0), so by replacing any
                    # existing time component with that, the result of
                    # TruncDate can be compared to DateField.
                    "T00:00:00.000",
                ]
            },
        }
    }


def trunc_time(self, compiler, connection):
    lhs_mql = process_lhs(self, compiler, connection, as_expr=True)
    date_to_string = {"format": "%H:%M:%S.%L", "date": lhs_mql}
    if tzname := self.get_tzname():
        date_to_string["timezone"] = tzname
    return {
        "$dateFromString": {
            "dateString": {
                "$concat": [
                    # Times are stored with date(1, 1, 1)), so by
                    # replacing any existing date component with that, the
                    # result of TruncTime can be compared to TimeField.
                    "0001-01-01T",
                    {"$dateToString": date_to_string},
                ]
            }
        }
    }


def register_datetime():
    Extract.as_mql_expr = extract
    ExtractQuarter.as_mql_expr = extract_quarter
    Now.as_mql_expr = now
    TruncBase.as_mql_expr = trunc
    TruncBase.convert_value = trunc_convert_value
    TruncDate.as_mql_expr = trunc_date
    TruncTime.as_mql_expr = trunc_time
