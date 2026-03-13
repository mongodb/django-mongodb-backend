from django.db import models

from django_mongodb_backend.fields import (
    EmbeddedModelArrayField,
    EmbeddedModelField,
    PolymorphicEmbeddedModelArrayField,
    PolymorphicEmbeddedModelField,
)
from django_mongodb_backend.models import EmbeddedModel


class Address(EmbeddedModel):
    city = models.CharField(max_length=20)
    state = models.CharField(max_length=2)
    zip_code = models.IntegerField()


class Author(EmbeddedModel):
    name = models.CharField(max_length=10)
    age = models.IntegerField()
    address = EmbeddedModelField(Address)


class Book(models.Model):
    name = models.CharField(max_length=100)
    author = EmbeddedModelField(Author)


# EmbeddedModelArrayField
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
    favorite_toy = PolymorphicEmbeddedModelField(["Bone"], blank=True, null=True)
    toys = PolymorphicEmbeddedModelArrayField(["Bone"], blank=True, null=True)

    def __str__(self):
        return self.name


class Cat(EmbeddedModel):
    name = models.CharField(max_length=100, db_column="name_")
    purs = models.BooleanField(default=True)
    weight = models.DecimalField(max_digits=4, decimal_places=2, blank=True, null=True)
    favorite_toy = PolymorphicEmbeddedModelField(["Mouse"], blank=True, null=True)
    toys = PolymorphicEmbeddedModelArrayField(["Mouse"], blank=True, null=True)

    def __str__(self):
        return self.name


class Bone(EmbeddedModel):
    brand = models.CharField(max_length=100)

    def __str__(self):
        return self.brand


class Mouse(EmbeddedModel):
    manufacturer = models.CharField(max_length=100)

    def __str__(self):
        return self.manufacturer


# PolymorphicEmbeddedModelArrayField
class Owner(models.Model):
    name = models.CharField(max_length=100)
    pets = PolymorphicEmbeddedModelArrayField(("Dog", "Cat"), blank=True, null=True)

    def __str__(self):
        return self.name
