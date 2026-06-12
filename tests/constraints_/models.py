from django.db import models

from django_mongodb_backend.fields import (
    ArrayField,
    EmbeddedModelArrayField,
    EmbeddedModelField,
    ObjectIdField,
    PolymorphicEmbeddedModelArrayField,
    PolymorphicEmbeddedModelField,
)
from django_mongodb_backend.models import EmbeddedModel


class UniqueFields(models.Model):
    array_value = ArrayField(models.IntegerField(), unique=True, null=True)
    binary = models.BinaryField(unique=True, null=True)
    boolean = models.BooleanField(unique=True, null=True)
    data = models.JSONField(unique=True, default=dict)
    date_value = models.DateField(unique=True, null=True)
    decimal_value = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        unique=True,
        null=True,
    )
    float_value = models.FloatField(unique=True, null=True)
    integer = models.IntegerField(unique=True, null=True)
    object_id = ObjectIdField(unique=True, null=True)
    small_int = models.SmallIntegerField(unique=True, null=True)
    text = models.TextField(unique=True, null=True)


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


# PolymorphicEmbeddedModelField
class Person(models.Model):
    name = models.CharField(max_length=100)
    pet = PolymorphicEmbeddedModelField(("Dog", "Cat"), blank=True, null=True)

    def __str__(self):
        return self.name


class Dog(EmbeddedModel):
    name = models.CharField(max_length=100)
    barks = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Cat(EmbeddedModel):
    name = models.CharField(max_length=100, db_column="name_")
    purs = models.BooleanField(default=True)
    weight = models.DecimalField(max_digits=4, decimal_places=2, blank=True, null=True)

    def __str__(self):
        return self.name


# PolymorphicEmbeddedModelArrayField
class Owner(models.Model):
    name = models.CharField(max_length=100)
    pets = PolymorphicEmbeddedModelArrayField(("Dog", "Cat"), blank=True, null=True)

    def __str__(self):
        return self.name


# Mixed/nested embedded fields
class Address(EmbeddedModel):
    street = models.CharField(max_length=50)
    tags = EmbeddedModelArrayField("Tag")


class Tag(EmbeddedModel):
    name = models.CharField(max_length=50)


class Store(models.Model):
    name = models.CharField(max_length=50)
    thing = PolymorphicEmbeddedModelField((Address, Tag))
