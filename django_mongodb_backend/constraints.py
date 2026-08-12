import datetime
import sys
from collections import defaultdict

from bson import ObjectId
from bson.decimal128 import Decimal128
from django.core import checks
from django.core.exceptions import FieldDoesNotExist
from django.db.models import UniqueConstraint
from pymongo import ASCENDING
from pymongo.operations import IndexModel

from .fields import EmbeddedModelArrayField, PolymorphicEmbeddedModelArrayField
from .indexes import EmbeddedFieldIndexMixin, _get_condition_mql, get_field


def _get_partial_unique_filter(field, connection):
    """
    Create unique constraints in a way that the query planner can use to avoid
    a collection scan. Works for all of the built-in field types except array,
    binData, and object.
    """
    db_type = field.db_type(connection)
    match db_type:
        case "bool":
            return {"$in": [True, False]}
        case "date":
            return {
                "$gte": datetime.datetime.min,
                "$lte": datetime.datetime.max,
            }
        case "decimal":
            return {
                "$gte": Decimal128("-9999999999999999999999999999999999E6111"),
                "$lte": Decimal128("9999999999999999999999999999999999E6111"),
            }
        case "double":
            return {
                "$gte": -sys.float_info.max,
                "$lte": sys.float_info.max,
            }
        case "int":
            return {
                "$gte": -2147483648,  # 32 bit integer range
                "$lte": 2147483647,
            }
        case "long":
            return {
                "$gte": -9223372036854775808,  # 64 bit integer range
                "$lte": 9223372036854775807,
            }
        case "objectId":
            return {
                "$gte": ObjectId("000000000000000000000000"),
                "$lte": ObjectId("ffffffffffffffffffffffff"),
            }
        case "string":
            return {"$gte": ""}  # Match all strings, including empty string.
        case _:  # e.g. array, binData, object
            # $type isn't used by the query planner.
            return {"$type": db_type}


def get_pymongo_index_model(self, model, schema_editor, field=None):
    """Return a pymongo IndexModel for this UniqueConstraint."""
    if self.contains_expressions:
        return None
    kwargs = {}
    filter_expression = defaultdict(dict)
    if self.condition:
        filter_expression.update(self._get_condition_mql(model, schema_editor))
    if self.nulls_distinct is None or self.nulls_distinct:
        # Indexing on $type matches the value of most SQL databases by allowing
        # multiple null values for the unique constraint. nulls_distinct will
        # be True or False for a UniqueConstraint, or None for
        # Field(unique=True) or Meta.unique_together.
        if field:
            filter_expression[field.column].update(
                _get_partial_unique_filter(field, schema_editor.connection)
            )
        else:
            for field_name in self.fields:
                field_ = get_field(model, field_name)
                filter_expression[field_.column].update(
                    _get_partial_unique_filter(field_.field, schema_editor.connection)
                )
    if filter_expression:
        kwargs["partialFilterExpression"] = filter_expression
    index_orders = (
        [(field.column, ASCENDING)]
        if field
        else [(get_field(model, field_name).column, ASCENDING) for field_name in self.fields]
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
                # Get the top-level field, removing paths to embedded fields.
                local_field_name, *_ = field_name.split(".")
                try:
                    field = model._meta.get_field(local_field_name)
                except FieldDoesNotExist:
                    continue
                if isinstance(field, (EmbeddedModelArrayField, PolymorphicEmbeddedModelArrayField)):
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
