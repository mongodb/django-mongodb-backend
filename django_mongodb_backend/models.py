from django.db import NotSupportedError, models

from .managers import EmbeddedModelManager


class EmbeddedModel(models.Model):
    objects = EmbeddedModelManager()

    class Meta:
        abstract = True

    def delete(self, *args, **kwargs):
        raise NotSupportedError("EmbeddedModels cannot be deleted.")

    def save(self, *args, **kwargs):
        raise NotSupportedError("EmbeddedModels cannot be saved.")


class EncryptedModelBase(models.base.ModelBase):
    def __new__(cls, name, bases, attrs, **kwargs):
        new_class = super().__new__(cls, name, bases, attrs, **kwargs)

        # Build a map of encrypted fields
        encrypted_fields = {
            "fields": {
                field.name: field.__class__.__name__
                for field in new_class._meta.fields
                if getattr(field, "encrypted", False)
            }
        }

        # Store it as a class-level attribute
        new_class.encrypted_fields_map = encrypted_fields
        return new_class


class EncryptedModel(models.Model, metaclass=EncryptedModelBase):
    class Meta:
        abstract = True
