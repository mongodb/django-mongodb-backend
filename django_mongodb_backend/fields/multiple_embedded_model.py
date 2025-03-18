from ..forms import MultipleEmbeddedModelFormField
from . import EmbeddedModelField
from .array import ArrayField


class MultipleEmbeddedModelField(ArrayField):
    def __init__(self, model, **kwargs):
        super().__init__(EmbeddedModelField(model), **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        if (
            path
            == "django_mongodb_backend.fields.multiple_embedded_model.MultipleEmbeddedModelField"
        ):
            path = "django_mongodb_backend.fields.MultipleEmbeddedModelField"
        kwargs.update(
            {
                "model": self.base_field.embedded_model,
                "size": self.size,
            }
        )
        del kwargs["base_field"]
        return name, path, args, kwargs

    def formfield(self, **kwargs):
        return super().formfield(
            **{
                "form_class": MultipleEmbeddedModelFormField,
                "model": self.base_field.embedded_model,
                "max_length": self.size,
                "prefix": self.name,
                **kwargs,
            }
        )
