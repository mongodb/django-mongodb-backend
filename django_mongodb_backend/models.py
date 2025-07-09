from django.conf import settings
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


class EncryptedModel(models.Model):
    encrypted = True

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        kwargs.setdefault("using", settings.ENCRYPTED_DB_ALIAS)
        super().save(*args, **kwargs)
