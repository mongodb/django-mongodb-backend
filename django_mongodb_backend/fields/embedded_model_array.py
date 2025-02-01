import difflib

from django.core.exceptions import FieldDoesNotExist
from django.db.models import Field, lookups
from django.db.models.expressions import Col
from django.db.models.lookups import Lookup, Transform

from .. import forms
from ..query_utils import process_lhs, process_rhs
from . import EmbeddedModelField
from .array import ArrayField


class EmbeddedModelArrayField(ArrayField):
    ALLOWED_LOOKUPS = {"exact", "len", "overlap"}

    def __init__(self, embedded_model, **kwargs):
        if "size" in kwargs:
            raise ValueError("EmbeddedModelArrayField does not support size.")
        super().__init__(EmbeddedModelField(embedded_model), **kwargs)
        self.embedded_model = embedded_model

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        if path == "django_mongodb_backend.fields.embedded_model_array.EmbeddedModelArrayField":
            path = "django_mongodb_backend.fields.EmbeddedModelArrayField"
        kwargs["embedded_model"] = self.embedded_model
        del kwargs["base_field"]
        return name, path, args, kwargs

    def get_db_prep_value(self, value, connection, prepared=False):
        if isinstance(value, list | tuple):
            # Must call get_db_prep_save() rather than get_db_prep_value()
            # to transform model instances to dicts.
            return [self.base_field.get_db_prep_save(i, connection) for i in value]
        if value is not None:
            raise TypeError(
                f"Expected list of {self.embedded_model!r} instances, not {type(value)!r}."
            )
        return value

    def formfield(self, **kwargs):
        # Skip ArrayField.formfield() which has some differeences, including
        # unneeded "base_field" and "max_length" instead of "max_num".
        return Field.formfield(
            self,
            **{
                "form_class": forms.EmbeddedModelArrayField,
                "model": self.base_field.embedded_model,
                "max_num": self.max_size,
                "prefix": self.name,
                **kwargs,
            },
        )

    def get_transform(self, name):
        transform = super().get_transform(name)
        if transform:
            return transform
        return KeyTransformFactory(name, self)

    def get_lookup(self, name):
        return super().get_lookup(name) if name in self.ALLOWED_LOOKUPS else None


class EMFArrayRHSMixin:
    def process_rhs(self, compiler, connection):
        values = self.rhs
        # Value must be serealized based on the query target.
        # If querying a subfield inside the array (i.e., a nested KeyTransform), use the output
        # field of the subfield. Otherwise, use the base field of the array itself.
        if isinstance(self.lhs, KeyTransform):
            get_db_prep_value = self.lhs._lhs.output_field.get_db_prep_value
        else:
            get_db_prep_value = self.lhs.output_field.base_field.get_db_prep_value
        return None, [get_db_prep_value(values, connection, prepared=True)]


@EmbeddedModelArrayField.register_lookup
class EMFArrayExact(EMFArrayRHSMixin, lookups.Exact):
    def as_mql(self, compiler, connection):
        if not isinstance(self.lhs, KeyTransform):
            raise ValueError("error")
        lhs_mql, inner_lhs_mql = process_lhs(self, compiler, connection)
        value = process_rhs(self, compiler, connection)
        return {
            "$anyElementTrue": {
                "$ifNull": [
                    {
                        "$map": {
                            "input": lhs_mql,
                            "as": "item",
                            "in": {"$eq": [inner_lhs_mql, value]},
                        }
                    },
                    [],
                ]
            }
        }


@EmbeddedModelArrayField.register_lookup
class ArrayOverlap(EMFArrayRHSMixin, Lookup):
    lookup_name = "overlap"

    def as_mql(self, compiler, connection):
        # Querying a subfield within the array elements (via nested KeyTransform).
        # Replicates MongoDB's implicit ANY-match by mapping over the array and applying
        # `$in` on the subfield.
        if not isinstance(self.lhs, KeyTransform):
            raise ValueError()
        lhs_mql = process_lhs(self, compiler, connection)
        values = process_rhs(self, compiler, connection)
        lhs_mql, inner_lhs_mql = lhs_mql
        return {
            "$anyElementTrue": {
                "$ifNull": [
                    {
                        "$map": {
                            "input": lhs_mql,
                            "as": "item",
                            "in": {"$in": [inner_lhs_mql, values]},
                        }
                    },
                    [],
                ]
            }
        }


class KeyTransform(Transform):
    def __init__(self, key_name, array_field, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.array_field = array_field
        self.key_name = key_name
        # The iteration items begins from the base_field, a virtual column with
        # base field output type is created.
        column_target = array_field.embedded_model._meta.get_field(key_name).clone()
        column_name = f"$item.{key_name}"
        column_target.db_column = column_name
        column_target.set_attributes_from_name(column_name)
        self._lhs = Col(None, column_target)
        self._sub_transform = None

    def __call__(self, this, *args, **kwargs):
        self._lhs = self._sub_transform(self._lhs, *args, **kwargs)
        return self

    def get_lookup(self, name):
        return self.output_field.get_lookup(name)

    def _get_missing_field_or_lookup_exception(self, lhs, name):
        suggested_lookups = difflib.get_close_matches(name, lhs.get_lookups())
        if suggested_lookups:
            suggested_lookups = " or ".join(suggested_lookups)
            suggestion = f", perhaps you meant {suggested_lookups}?"
        else:
            suggestion = ""
        raise FieldDoesNotExist(
            f"Unsupported lookup '{name}' for "
            f"EmbeddedModelArrayField of '{lhs.__class__.__name__}'"
            f"{suggestion}"
        )

    def get_transform(self, name):
        """
        Validate that `name` is either a field of an embedded model or a
        lookup on an embedded model's field.
        """
        # Once the sub lhs is a transform, all the filter are applied over it.
        # Otherwise get transform from EMF.
        if transform := self._lhs.get_transform(name):
            self._sub_transform = transform
            return self
        raise self._get_missing_field_or_lookup_exception(self._lhs.output_field, name)

    def as_mql(self, compiler, connection):
        inner_lhs_mql = self._lhs.as_mql(compiler, connection)
        lhs_mql = process_lhs(self, compiler, connection)
        return lhs_mql, inner_lhs_mql

    @property
    def output_field(self):
        return self.array_field


class KeyTransformFactory:
    def __init__(self, key_name, base_field):
        self.key_name = key_name
        self.base_field = base_field

    def __call__(self, *args, **kwargs):
        return KeyTransform(self.key_name, self.base_field, *args, **kwargs)
