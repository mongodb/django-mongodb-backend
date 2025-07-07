from django.db import models

from django_mongodb_backend.fields import EncryptedCharField
from django_mongodb_backend.models import EncryptedModel


class Person(EncryptedModel):
    name = models.CharField("name", max_length=100)
    ssn = EncryptedCharField("ssn", max_length=11, queries=["equality"])
    ssn2 = EncryptedCharField("ssn", max_length=11, queries=["equality"])

    class Meta:
        required_db_features = {"supports_queryable_encryption"}

    def __str__(self):
        return self.name
