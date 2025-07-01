import contextlib

from django.core.exceptions import FieldDoesNotExist
from django.db.models.expressions import Col
from django.db.models.fields.related import lazy_related_operation
from django.db.models.lookups import Lookup, Transform

from . import PolymorphicEmbeddedModelField
from .array import ArrayField, ArrayLenTransform
from .embedded_model_array import KeyTransform as ArrayFieldKeyTransform
from .embedded_model_array import KeyTransformFactory as ArrayFieldKeyTransformFactory


class PolymorphicEmbeddedModelArrayField(ArrayField):
    def __init__(self, embedded_models, **kwargs):
        if "size" in kwargs:
            raise ValueError("PolymorphicEmbeddedModelArrayField does not support size.")
        kwargs["editable"] = False
        super().__init__(PolymorphicEmbeddedModelField(embedded_models), **kwargs)
        self.embedded_models = embedded_models

    def contribute_to_class(self, cls, name, private_only=False, **kwargs):
        super().contribute_to_class(cls, name, private_only=private_only, **kwargs)

        if not cls._meta.abstract:
            # If embedded_models contains any strings, replace them with the actual
            # model classes.
            def _resolve_lookup(_, *resolved_models):
                self.embedded_models = resolved_models

            lazy_related_operation(_resolve_lookup, cls, *self.embedded_models)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        if path == (
            "django_mongodb_backend.fields.polymorphic_embedded_model_array."
            "PolymorphicEmbeddedModelArrayField"
        ):
            path = "django_mongodb_backend.fields.PolymorphicEmbeddedModelArrayField"
        kwargs["embedded_models"] = self.embedded_models
        del kwargs["base_field"]
        del kwargs["editable"]
        return name, path, args, kwargs

    def get_db_prep_value(self, value, connection, prepared=False):
        if isinstance(value, list | tuple):
            # Must call get_db_prep_save() rather than get_db_prep_value()
            # to transform model instances to dicts.
            return [self.base_field.get_db_prep_save(i, connection) for i in value]
        if value is not None:
            raise TypeError(
                f"Expected list of {self.embedded_models!r} instances, not {type(value)!r}."
            )
        return value

    def formfield(self, **kwargs):
        raise NotImplementedError("PolymorphicEmbeddedModelField does not support forms.")

    _get_model_from_label = PolymorphicEmbeddedModelField._get_model_from_label

    def get_transform(self, name):
        transform = super().get_transform(name)
        if transform:
            return transform
        return KeyTransformFactory(name, self)

    def _get_lookup(self, lookup_name):
        lookup = super()._get_lookup(lookup_name)
        if lookup is None or lookup is ArrayLenTransform:
            return lookup

        class EmbeddedModelArrayFieldLookups(Lookup):
            def as_mql(self, compiler, connection):
                raise ValueError(
                    "Lookups aren't supported on PolymorphicEmbeddedModelArrayField. "
                    "Try querying one of its embedded fields instead."
                )

        return EmbeddedModelArrayFieldLookups


class KeyTransform(ArrayFieldKeyTransform):
    field_class_name = "PolymorphicEmbeddedModelArrayField"

    def __init__(self, key_name, array_field, *args, **kwargs):
        # Skip ArrayFieldKeyTransform.__init__()
        Transform.__init__(self, *args, **kwargs)
        self.array_field = array_field
        self.key_name = key_name
        for model in array_field.base_field.embedded_models:
            with contextlib.suppress(FieldDoesNotExist):
                field = model._meta.get_field(key_name)
                break
        else:
            raise FieldDoesNotExist(
                f"The models of field '{array_field.name}' have no field named '{key_name}'."
            )
        # Lookups iterate over the array of embedded models. A virtual column
        # of the queried field's type represents each element.
        column_target = field.clone()
        column_name = f"$item.{key_name}"
        column_target.db_column = column_name
        column_target.set_attributes_from_name(column_name)
        self._lhs = Col(None, column_target)
        self._sub_transform = None


class KeyTransformFactory(ArrayFieldKeyTransformFactory):
    def __call__(self, *args, **kwargs):
        return KeyTransform(self.key_name, self.base_field, *args, **kwargs)
