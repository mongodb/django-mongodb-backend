from django.db import models

from django_mongodb_backend.fields import EmbeddedModelField
from django_mongodb_backend.models import EmbeddedModel


class Address(EmbeddedModel):
    po_box = models.CharField(max_length=50, blank=True, verbose_name="PO Box")
    city = models.CharField(max_length=20)
    state = models.CharField(max_length=2)
    zip_code = models.IntegerField()


class Author(models.Model):
    name = models.CharField(max_length=10)
    age = models.IntegerField()
    address = EmbeddedModelField(Address)
    billing_address = EmbeddedModelField(Address, blank=True, null=True)


class Publisher(EmbeddedModel):
    name = models.CharField(max_length=50)
    address = EmbeddedModelField(Address)


class Book(models.Model):
    title = models.CharField(max_length=50)
    publisher = EmbeddedModelField(Publisher)
