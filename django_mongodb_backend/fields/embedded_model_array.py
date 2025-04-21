from ..forms import EmbeddedModelArrayFormField
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
        # TODO: ...
        return self.base_field.get_transform(name)
        # Copied from EmbedddedModelField -- customize?
        #        transform = super().get_transform(name)
        #        if transform:
        #            return transform
        #        field = self.embedded_model._meta.get_field(name)
        #        return KeyTransformFactory(name, field)


@EmbeddedModelArrayField.register_lookup
class EMFArrayExact(EMFExact):
    # TODO
    pass
