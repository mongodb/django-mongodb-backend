from django.db import NotSupportedError
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


def trunc_date(self, compiler, connection):
    # Cast to date rather than truncate to date.
    lhs_mql = process_lhs(self, compiler, connection, as_expr=True)
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
    lhs_mql = process_lhs(self, compiler, connection, as_expr=True)
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


def register_datetime():
    Extract.as_mql_expr = extract
    ExtractQuarter.as_mql_expr = extract_quarter
    Now.as_mql_expr = now
    TruncBase.as_mql_expr = trunc
    TruncDate.as_mql_expr = trunc_date
    TruncTime.as_mql_expr = trunc_time
