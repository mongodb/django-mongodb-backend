import datetime
from collections import defaultdict

from django.core import checks
from django.core.exceptions import FieldDoesNotExist
from django.db.models import UniqueConstraint
from pymongo import ASCENDING
from pymongo.operations import IndexModel

from .fields import EmbeddedModelArrayField, PolymorphicEmbeddedModelArrayField
from .indexes import EmbeddedFieldIndexMixin, _get_condition_mql, get_field


def _get_partial_unique_filter(field_or_field_column, connection):
    field = getattr(field_or_field_column, "field", field_or_field_column)
    db_type = field.db_type(connection)

    match db_type:
        case "string":
            return {"$gte": ""}
        case "int":
            return {"$gte": -2147483648, "$lte": 2147483647}
        case "long":
            return {
                "$gte": -9223372036854775808,
                "$lte": 9223372036854775807,
            }
        case "bool":
            return {"$in": [True, False]}
        case "date":
            return {
                "$gte": datetime.datetime.min,
                "$lte": datetime.datetime.max,
            }
        case _:
            return {"$type": db_type}


def _add_nullable_unique_filter(filter_expression, field_or_field_column, connection, column):
    field = getattr(field_or_field_column, "field", field_or_field_column)
    if not field.null:
        return
    filter_expression[column].update(_get_partial_unique_filter(field_or_field_column, connection))


def get_pymongo_index_model(self, model, schema_editor, field=None, column_prefix=""):
    """Return a pymongo IndexModel for this UniqueConstraint."""
    if self.contains_expressions:
        return None
    kwargs = {}
    filter_expression = defaultdict(dict)
    if self.condition:
        filter_expression.update(self._get_condition_mql(model, schema_editor))
    if self.nulls_distinct is None or self.nulls_distinct:
        if field:
            column = column_prefix + field.column
            _add_nullable_unique_filter(filter_expression, field, schema_editor.connection, column)
        else:
            for field_name in self.fields:
                field_ = get_field(model, field_name)
                _add_nullable_unique_filter(
                    filter_expression,
                    field_,
                    schema_editor.connection,
                    field_.column,
                )
    if filter_expression:
        kwargs["partialFilterExpression"] = filter_expression
    index_orders = (
        [(column_prefix + field.column, ASCENDING)]
        if field
        else [
            (column_prefix + get_field(model, field_name).column, ASCENDING)
            for field_name in self.fields
        ]
    )
    return IndexModel(index_orders, name=self.name, unique=True, **kwargs)


class EmbeddedFieldUniqueConstraint(EmbeddedFieldIndexMixin, UniqueConstraint):
    meta_option_name = "constraints"

    def check(self, model, connection):
        errors = super().check(model, connection)
        # Due to MongoDB limitation (https://jira.mongodb.org/browse/SERVER-17853),
        # EmbeddedFieldUniqueConstraint cannot reference subfields of
        # EmbeddedModelArrayField unless nulls_distinct=False (so that the
        # index doesn't need to be created with a partialFilterExpression).
        if self.nulls_distinct is not False:
            for field_name in self.fields:
                local_field_name, *_ = field_name.split(".")
                try:
                    field = model._meta.get_field(local_field_name)
                except FieldDoesNotExist:
                    continue
                if isinstance(
                    field,
                    (EmbeddedModelArrayField, PolymorphicEmbeddedModelArrayField),
                ):
                    errors.append(
                        checks.Error(
                            f"EmbeddedFieldUniqueConstraint {self.name!r} must "
                            "have nulls_distinct=False since it references "
                            f"{field.__class__.__name__} '{local_field_name}'.",
                            obj=model,
                            id="mongodb.constraints.embedded_unique.E001",
                        )
                    )
        return errors


def register_constraints():
    UniqueConstraint.get_pymongo_index_model = get_pymongo_index_model
    UniqueConstraint._get_condition_mql = _get_condition_mql
