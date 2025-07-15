from django.db import models

from django_mongodb_backend.encryption import QueryType
from django_mongodb_backend.fields import EncryptedCharField, EncryptedIntegerField
from django_mongodb_backend.models import EncryptedModel


class Billing(EncryptedModel):
    class Meta:
        required_db_features = {"supports_queryable_encryption"}

    # TODO: Add fields for billing information


class PatientRecord(EncryptedModel):
    class Meta:
        required_db_features = {"supports_queryable_encryption"}

    ssn = EncryptedCharField("ssn", max_length=11, queries=QueryType.equality())

    # TODO: Embed Billing model
    # billing =


class Patient(EncryptedModel):
    class Meta:
        required_db_features = {"supports_queryable_encryption"}

    def __str__(self):
        return self.name

    patient_id = EncryptedIntegerField("patient_id")
    patient_age = EncryptedIntegerField("patient_age", queries=QueryType.range())
    patient_name = EncryptedCharField("name", max_length=100)

    # TODO: Embed PatientRecord model
    # patient_record =


# Via django/tests/model_fields/models.py
class Post(EncryptedModel):
    title = EncryptedCharField(max_length=100)
    body = models.TextField()


class IntegerModel(EncryptedModel):
    value = EncryptedIntegerField()
