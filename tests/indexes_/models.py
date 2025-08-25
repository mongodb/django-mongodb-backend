from django.db import models

from django_mongodb_backend.fields import (
    ArrayField,
    EmbeddedModelArrayField,
    EmbeddedModelField,
    ObjectIdField,
)
from django_mongodb_backend.models import EmbeddedModel


class Article(models.Model):
    headline = models.CharField(max_length=100)
    number = models.IntegerField()
    body = models.TextField()


class Data(EmbeddedModel):
    integer = models.IntegerField()
    string = models.CharField(max_length=100, db_column="string_")


class SearchIndexTestModel(models.Model):
    big_integer = models.BigIntegerField()
    binary = models.BinaryField()
    boolean = models.BooleanField()
    char = models.CharField(max_length=100)
    datetime = models.DateTimeField(auto_now=True)
    embedded_model = EmbeddedModelField(Data)
    float = models.FloatField()
    integer = models.IntegerField()
    json = models.JSONField()
    object_id = ObjectIdField()
    vector_float = ArrayField(models.FloatField(), size=10)
    vector_integer = ArrayField(models.IntegerField(), size=10)


class DataHolder(models.Model):
    integer = models.IntegerField()
    data = EmbeddedModelField(Data)


class Movie(models.Model):
    title = models.CharField(max_length=255)
    reviews = EmbeddedModelArrayField("Review", null=True)

    def __str__(self):
        return self.title


class Review(EmbeddedModel):
    title = models.CharField(max_length=255, db_column="title_")
    rating = models.DecimalField(max_digits=6, decimal_places=1)

    def __str__(self):
        return self.title
