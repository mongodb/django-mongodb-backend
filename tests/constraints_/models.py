from django.db import models

from django_mongodb_backend.fields import EmbeddedModelArrayField, EmbeddedModelField
from django_mongodb_backend.models import EmbeddedModel


class Data(EmbeddedModel):
    integer = models.IntegerField(null=True)


class DataHolder(models.Model):
    integer = models.IntegerField(null=True)
    data = EmbeddedModelField(Data)


class Movie(models.Model):
    title = models.CharField(max_length=255)
    reviews = EmbeddedModelArrayField("Review", null=True)

    def __str__(self):
        return self.title


class Review(EmbeddedModel):
    title = models.CharField(max_length=255)
    rating = models.DecimalField(max_digits=6, decimal_places=1)

    def __str__(self):
        return self.title
