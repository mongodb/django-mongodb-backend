from django.db import models

from django_mongodb_backend.fields import EmbeddedModelField
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
