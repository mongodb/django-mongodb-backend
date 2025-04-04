from django.db import NotSupportedError, models

from .managers import EmbeddedModelManager


class EMBEDDED:
    pass


class EmbeddedModel(models.Model):
    objects = EmbeddedModelManager()

    class Meta:
        abstract = True
        db_table = EMBEDDED

    def delete(self, *args, **kwargs):
        raise NotSupportedError("EmbeddedModels cannot be deleted.")

    def save(self, *args, **kwargs):
        raise NotSupportedError("EmbeddedModels cannot be saved.")
