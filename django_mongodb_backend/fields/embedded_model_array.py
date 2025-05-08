import difflib

from django.core.exceptions import FieldDoesNotExist
from django.db import models
from django.db.models.expressions import Col
from django.db.models.lookups import Transform

from ..forms import EmbeddedModelArrayFormField
from ..query_utils import process_lhs, process_rhs
from . import EmbeddedModelField
from .array import ArrayField
from .embedded_model import EMFExact


class EmbeddedModelArrayField(ArrayField):
    def __init__(self, model, **kwargs):
        super().__init__(EmbeddedModelField(model), **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        if path == "django_mongodb_backend.fields.multiple_embedded_model.EmbeddedModelArrayField":
            path = "django_mongodb_backend.fields.EmbeddedModelArrayField"
        kwargs.update(
            {
                "model": self.base_field.embedded_model,
                "size": self.size,
            }
        )
        del kwargs["base_field"]
        return name, path, args, kwargs

    def get_db_prep_value(self, value, connection, prepared=False):
        if isinstance(value, list | tuple):
            return [self.base_field.get_db_prep_save(i, connection) for i in value]
        return value

    def formfield(self, **kwargs):
        return super().formfield(
            **{
                "form_class": EmbeddedModelArrayFormField,
                "model": self.base_field.embedded_model,
                "max_length": self.size,
                "prefix": self.name,
                **kwargs,
            }
        )

    def get_transform(self, name):
        transform = super().get_transform(name)
        if transform:
            return transform
        field = self.base_field.embedded_model._meta.get_field(name)
        return KeyTransformFactory(name, field)


@EmbeddedModelArrayField.register_lookup
class EMFArrayExact(EMFExact):
    def as_mql(self, compiler, connection):
        lhs_mql = process_lhs(self, compiler, connection)
        value = process_rhs(self, compiler, connection)
        if isinstance(self.lhs, Col | KeyTransform):
            if isinstance(value, models.Model):
                value, emf_data = self.model_to_dict(value)
                # Get conditions for any nested EmbeddedModelFields.
                conditions = self.get_conditions({lhs_mql[1]: (value, emf_data)})
                return {
                    "$anyElementTrue": {
                        "$ifNull": [
                            {
                                "$map": {
                                    "input": lhs_mql[0],
                                    "as": "item",
                                    "in": {"$and": conditions},
                                }
                            },
                            [],
                        ]
                    }
                }
            return {
                "$anyElementTrue": {
                    "$ifNull": [
                        {
                            "$map": {
                                "input": lhs_mql[0],
                                "as": "item",
                                "in": {"$eq": [lhs_mql[1], value]},
                            }
                        },
                        [],
                    ]
                }
            }
        return connection.mongo_operators[self.lookup_name](lhs_mql, value)


class KeyTransform(Transform):
    # it should be different class than EMF keytransform even most of the methods are equal.
    def __init__(self, key_name, base_field, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.base_field = base_field
        #  TODO: Need to create a column, will refactor this thing.
        column_target = base_field.clone()
        column_target.db_column = f"$item.{key_name}"
        column_target.set_attributes_from_name(f"$item.{key_name}")
        self._lhs = Col(None, column_target)
        self._sub_transform = None

    def __call__(self, this, *args, **kwargs):
        self._lhs = self._sub_transform(self._lhs, *args, **kwargs)
        return self

    def get_lookup(self, name):
        return self.output_field.get_lookup(name)

    def get_transform(self, name):
        """
        Validate that `name` is either a field of an embedded model or a
        lookup on an embedded model's field.
        """
        if isinstance(self._lhs, Transform):
            transform = self._lhs.get_transform(name)
        else:
            transform = self.base_field.get_transform(name)
        if transform:
            self._sub_transform = transform
            return self
        suggested_lookups = difflib.get_close_matches(name, self.base_field.get_lookups())
        if suggested_lookups:
            suggested_lookups = " or ".join(suggested_lookups)
            suggestion = f", perhaps you meant {suggested_lookups}?"
        else:
            suggestion = "."
        raise FieldDoesNotExist(
            f"Unsupported lookup '{name}' for "
            f"{self.base_field.__class__.__name__} '{self.base_field.name}'"
            f"{suggestion}"
        )

    def as_mql(self, compiler, connection):
        if isinstance(self._lhs, Transform):
            inner_lhs_mql = self._lhs.as_mql(compiler, connection)
        else:
            inner_lhs_mql = None
        lhs_mql = process_lhs(self, compiler, connection)
        return lhs_mql, inner_lhs_mql

    @property
    def output_field(self):
        return EmbeddedModelArrayField(self.base_field)


class KeyTransformFactory:
    def __init__(self, key_name, base_field):
        self.key_name = key_name
        self.base_field = base_field

    def __call__(self, *args, **kwargs):
        return KeyTransform(self.key_name, self.base_field, *args, **kwargs)
