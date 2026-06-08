from django.db import models

from django_mongodb_backend.fields import ArrayField, EmbeddedModelArrayField, EmbeddedModelField
from django_mongodb_backend.models import EmbeddedModel


class City(EmbeddedModel):
    name = models.CharField(max_length=100)
    population = models.IntegerField()


class Country(EmbeddedModel):
    name = models.CharField(max_length=100)
    capital = EmbeddedModelField(City, null=True, blank=True)
    cities = EmbeddedModelArrayField(City, null=True, blank=True)
    languages = ArrayField(models.CharField(max_length=50), null=True, blank=True)


class CityWithUniqueCode(EmbeddedModel):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10, unique=True)


class Continent(models.Model):
    name = models.CharField(max_length=100)
    country = EmbeddedModelField(Country, null=True, blank=True)
    countries = EmbeddedModelArrayField(Country, null=True, blank=True)
    notable_cities = ArrayField(models.CharField(max_length=100), null=True, blank=True)
