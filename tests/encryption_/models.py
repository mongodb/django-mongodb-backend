from django.db import models

from django_mongodb_backend.encryption import QueryTypes
from django_mongodb_backend.fields import EncryptedCharField
from django_mongodb_backend.models import EncryptedModel

# Query types for encrypted fields with optional parameters
query_types = QueryTypes()
queries = [query_types.equality(contention=1), query_types.range(sparsity=2, precision=3)]


class Person(EncryptedModel):
    name = models.CharField("name", max_length=100)
    ssn = EncryptedCharField("ssn", max_length=11, queries=queries)

    class Meta:
        required_db_features = {"supports_queryable_encryption"}

    def __str__(self):
        return self.name
