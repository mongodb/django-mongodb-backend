from django.db import models

from django_mongodb_backend.fields import (
    ArrayField,
    EmbeddedModelField,
)
from django_mongodb_backend.models import EmbeddedModel


class Writer(EmbeddedModel):
    name = models.CharField(max_length=10)


class Location(EmbeddedModel):
    type = models.CharField(default="Point", max_length=50)
    coordinates = ArrayField(models.FloatField(), max_size=2)


class Article(models.Model):
    headline = models.CharField(max_length=100)
    number = models.IntegerField()
    body = models.TextField()
    location = EmbeddedModelField(Location, null=True)
    plot_embedding = ArrayField(models.FloatField(), size=3, null=True)
    writer = EmbeddedModelField(Writer, null=True)
