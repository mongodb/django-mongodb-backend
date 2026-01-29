from collections import defaultdict

from django.db.models import UniqueConstraint
from pymongo import ASCENDING
from pymongo.operations import IndexModel

from .indexes import _get_condition_mql


def get_pymongo_index_model(self, model, schema_editor, field=None, column_prefix=""):
    """Return a pymongo IndexModel for this UniqueConstraint."""
    if self.contains_expressions:
        return None
    kwargs = {}
    filter_expression = defaultdict(dict)
    if self.condition:
        filter_expression.update(self._get_condition_mql(model, schema_editor))
    # Indexing on $type matches the value of most SQL databases by allowing
    # multiple null values for the unique constraint.
    if field:
        column = column_prefix + field.column
        filter_expression[column].update({"$type": field.db_type(schema_editor.connection)})
    else:
        for field_name in self.fields:
            field_ = model._meta.get_field(field_name)
            filter_expression[field_.column].update(
                {"$type": field_.db_type(schema_editor.connection)}
            )
    if filter_expression:
        kwargs["partialFilterExpression"] = filter_expression
    index_orders = (
        [(column_prefix + field.column, ASCENDING)]
        if field
        else [
            (column_prefix + model._meta.get_field(field_name).column, ASCENDING)
            for field_name in self.fields
        ]
    )
    return IndexModel(index_orders, name=self.name, unique=True, **kwargs)


def register_constraints():
    UniqueConstraint.get_pymongo_index_model = get_pymongo_index_model
    UniqueConstraint._get_condition_mql = _get_condition_mql
