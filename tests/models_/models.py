from django.db import models

from django_mongodb_backend.models import EmbeddedModel


class Embed(EmbeddedModel):
    pass


class PlainModel(models.Model):
    pass
