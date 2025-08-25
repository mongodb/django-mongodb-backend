from collections import defaultdict

from django.core import checks
from django.core.exceptions import FieldDoesNotExist
from django.db.models import UniqueConstraint
from pymongo import ASCENDING
from pymongo.operations import IndexModel

from .fields import EmbeddedModelArrayField
from .indexes import EmbeddedFieldIndexMixin, _get_condition_mql, get_field


def get_pymongo_index_model(self, model, schema_editor, field=None, column_prefix=""):
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
            column = column_prefix + field.column
            filter_expression[column].update({"$type": field.db_type(schema_editor.connection)})
        else:
            for field_name in self.fields:
                field_ = get_field(model, field_name)
                filter_expression[field_.column].update(
                    {"$type": field_.field.db_type(schema_editor.connection)}
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
                # Get the top-level field, removing paths to embedded fields.
                local_field_name, *_ = field_name.split(".")
                try:
                    field = model._meta.get_field(local_field_name)
                except FieldDoesNotExist:
                    continue
                if isinstance(field, EmbeddedModelArrayField):
                    errors.append(
                        checks.Error(
                            f"EmbeddedFieldUniqueConstraint {self.name!r} must "
                            "have nulls_distinct=False since it references "
                            f"EmbeddedModelArrayField '{local_field_name}'.",
                            obj=model,
                            id="django_mongodb_backend.constraints.E001",
                        )
                    )
        return errors


def register_constraints():
    UniqueConstraint.get_pymongo_index_model = get_pymongo_index_model
    UniqueConstraint._get_condition_mql = _get_condition_mql
