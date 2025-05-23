from django.db.models import Field

from .. import forms
from . import EmbeddedModelField
from .array import ArrayField


class EmbeddedModelArrayField(ArrayField):
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
