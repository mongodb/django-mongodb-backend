from django.db import models

from django_mongodb_backend.encryption import QueryType
from django_mongodb_backend.fields import EncryptedCharField
from django_mongodb_backend.models import EncryptedModel

qt = QueryType()
queries = [qt.equality(contention=1)]


class Person(EncryptedModel):
    name = models.CharField("name", max_length=100)
    ssn = EncryptedCharField("ssn", max_length=11, queries=queries)

    class Meta:
        required_db_features = {"supports_queryable_encryption"}

    def __str__(self):
        return self.name
