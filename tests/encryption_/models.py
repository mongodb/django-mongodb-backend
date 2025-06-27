from django.db import models

from django_mongodb_backend.fields import EncryptedCharField
from django_mongodb_backend.models import EncryptedModel


class Person(EncryptedModel):
    ssn = EncryptedCharField("ssn", max_length=11)
    name = models.CharField("name", max_length=100)

    def __str__(self):
        return self.ssn
