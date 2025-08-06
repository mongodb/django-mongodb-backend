from bson import Int64
from django.db.models.fields import DurationField

_get_db_prep_value = DurationField.get_db_prep_value


def get_db_prep_value(self, value, connection, prepared=False):
    """DurationField stores milliseconds rather than microseconds."""
    value = _get_db_prep_value(self, value, connection, prepared)
    if connection.vendor == "mongodb" and value is not None:
        value //= 1000
        # Store value as Int64 (long).
        value = Int64(value)
    return value


def register_duration_field():
    DurationField.get_db_prep_value = get_db_prep_value
