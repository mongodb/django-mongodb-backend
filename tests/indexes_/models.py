from django.db import models

from django_mongodb_backend.fields import ArrayField, EmbeddedModelField
from django_mongodb_backend.models import EmbeddedModel


class Data(EmbeddedModel):
    integer = models.IntegerField()


class Article(models.Model):
    headline = models.CharField(max_length=100)
    number = models.IntegerField()
    body = models.TextField()
    data = models.JSONField()
    embedded = EmbeddedModelField(Data)
    auto_now = models.DateTimeField(auto_now=True)
    title_embedded = ArrayField(models.FloatField(), size=10)
    description_embedded = ArrayField(models.FloatField(), size=10)
    number_list = ArrayField(models.FloatField())
    name_list = ArrayField(models.CharField(max_length=30), size=10)
