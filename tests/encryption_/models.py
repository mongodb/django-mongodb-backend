from django.db import models

from django_mongodb_backend.fields import (
    EncryptedBigIntegerField,
    EncryptedBinaryField,
    EncryptedBooleanField,
    EncryptedCharField,
    EncryptedDateField,
    EncryptedDateTimeField,
    EncryptedDecimalField,
    EncryptedDurationField,
    EncryptedEmailField,
    EncryptedEmbeddedModelField,
    EncryptedFloatField,
    EncryptedGenericIPAddressField,
    EncryptedIntegerField,
    EncryptedPositiveBigIntegerField,
    EncryptedPositiveIntegerField,
    EncryptedPositiveSmallIntegerField,
    EncryptedSmallIntegerField,
    EncryptedTextField,
    EncryptedTimeField,
    EncryptedURLField,
)
from django_mongodb_backend.models import EncryptedEmbeddedModel


class Billing(EncryptedEmbeddedModel):
    cc_type = models.CharField(max_length=50)
    cc_number = models.CharField(max_length=20)


class PatientRecord(EncryptedEmbeddedModel):
    ssn = EncryptedCharField(max_length=11, queries={"queryType": "equality"})
    billing = EncryptedEmbeddedModelField(Billing)


class Patient(models.Model):
    patient_name = models.CharField(max_length=255)
    patient_id = models.BigIntegerField()
    patient_record = EncryptedEmbeddedModelField(PatientRecord)

    def __str__(self):
        return f"{self.patient_name} ({self.patient_id})"


class EncryptedModel(models.Model):
    """
    Abstract base model for all Encrypted models
    that require the 'supports_queryable_encryption' DB feature.
    """

    class Meta:
        abstract = True
        required_db_features = {"supports_queryable_encryption"}


# Equality-queryable fields
class EncryptedBinaryTest(EncryptedModel):
    value = EncryptedBinaryField(queries={"queryType": "equality"})


class EncryptedBooleanTest(EncryptedModel):
    value = EncryptedBooleanField(queries={"queryType": "equality"})


class EncryptedCharTest(EncryptedModel):
    value = EncryptedCharField(max_length=255, queries={"queryType": "equality"})


class EncryptedEmailTest(EncryptedModel):
    value = EncryptedEmailField(max_length=255, queries={"queryType": "equality"})


class EncryptedGenericIPAddressTest(EncryptedModel):
    value = EncryptedGenericIPAddressField(queries={"queryType": "equality"})


class EncryptedTextTest(EncryptedModel):
    value = EncryptedTextField(queries={"queryType": "equality"})


class EncryptedURLTest(EncryptedModel):
    value = EncryptedURLField(max_length=500, queries={"queryType": "equality"})


# Range-queryable fields (also support equality)
class EncryptedBigIntegerTest(EncryptedModel):
    value = EncryptedBigIntegerField(queries={"queryType": "range"})


class EncryptedDateTest(EncryptedModel):
    value = EncryptedDateField(queries={"queryType": "range"})


class EncryptedDateTimeTest(EncryptedModel):
    value = EncryptedDateTimeField(queries={"queryType": "range"})


class EncryptedDecimalTest(EncryptedModel):
    value = EncryptedDecimalField(max_digits=10, decimal_places=2, queries={"queryType": "range"})


class EncryptedDurationTest(EncryptedModel):
    value = EncryptedDurationField(queries={"queryType": "range"})


class EncryptedFloatTest(EncryptedModel):
    value = EncryptedFloatField(queries={"queryType": "range"})


class EncryptedIntegerTest(EncryptedModel):
    value = EncryptedIntegerField(queries={"queryType": "range"})


class EncryptedPositiveBigIntegerTest(EncryptedModel):
    value = EncryptedPositiveBigIntegerField(queries={"queryType": "range"})


class EncryptedPositiveIntegerTest(EncryptedModel):
    value = EncryptedPositiveIntegerField(queries={"queryType": "range"})


class EncryptedPositiveSmallIntegerTest(EncryptedModel):
    value = EncryptedPositiveSmallIntegerField(queries={"queryType": "range"})


class EncryptedSmallIntegerTest(EncryptedModel):
    value = EncryptedSmallIntegerField(queries={"queryType": "range"})


class EncryptedTimeTest(EncryptedModel):
    value = EncryptedTimeField(queries={"queryType": "range"})
