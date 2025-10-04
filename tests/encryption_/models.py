from django.db import models

from django_mongodb_backend.fields import (
    EmbeddedModelField,
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
from django_mongodb_backend.models import EmbeddedModel


class EncryptedTestModel(models.Model):
    class Meta:
        abstract = True
        required_db_features = {"supports_queryable_encryption"}


class Patient(EncryptedTestModel):
    patient_name = models.CharField(max_length=255)
    patient_id = models.BigIntegerField()
    patient_record = EmbeddedModelField("PatientRecord")

    def __str__(self):
        return f"{self.patient_name} ({self.patient_id})"


class PatientRecord(EmbeddedModel):
    ssn = EncryptedCharField(max_length=11, queries={"queryType": "equality"})
    billing = EncryptedEmbeddedModelField("Billing")
    bill_amount = models.DecimalField(max_digits=10, decimal_places=2)


class Billing(EmbeddedModel):
    cc_type = models.CharField(max_length=50)
    cc_number = models.CharField(max_length=20)


# Equality-queryable fields
class BinaryModel(EncryptedTestModel):
    value = EncryptedBinaryField(queries={"queryType": "equality"})


class BooleanModel(EncryptedTestModel):
    value = EncryptedBooleanField(queries={"queryType": "equality"})


class CharModel(EncryptedTestModel):
    value = EncryptedCharField(max_length=255, queries={"queryType": "equality"})


class EmailModel(EncryptedTestModel):
    value = EncryptedEmailField(max_length=255, queries={"queryType": "equality"})


class GenericIPAddressModel(EncryptedTestModel):
    value = EncryptedGenericIPAddressField(queries={"queryType": "equality"})


class TextModel(EncryptedTestModel):
    value = EncryptedTextField(queries={"queryType": "equality"})


class URLModel(EncryptedTestModel):
    value = EncryptedURLField(max_length=500, queries={"queryType": "equality"})


# Range-queryable fields (also support equality)
class BigIntegerModel(EncryptedTestModel):
    value = EncryptedBigIntegerField(queries={"queryType": "range"})


class DateModel(EncryptedTestModel):
    value = EncryptedDateField(queries={"queryType": "range"})


class DateTimeModel(EncryptedTestModel):
    value = EncryptedDateTimeField(queries={"queryType": "range"})


class DecimalModel(EncryptedTestModel):
    value = EncryptedDecimalField(max_digits=10, decimal_places=2, queries={"queryType": "range"})


class DurationModel(EncryptedTestModel):
    value = EncryptedDurationField(queries={"queryType": "range"})


class FloatModel(EncryptedTestModel):
    value = EncryptedFloatField(queries={"queryType": "range"})


class IntegerModel(EncryptedTestModel):
    value = EncryptedIntegerField(queries={"queryType": "range"})


class PositiveBigIntegerModel(EncryptedTestModel):
    value = EncryptedPositiveBigIntegerField(queries={"queryType": "range"})


class PositiveIntegerModel(EncryptedTestModel):
    value = EncryptedPositiveIntegerField(queries={"queryType": "range"})


class PositiveSmallIntegerModel(EncryptedTestModel):
    value = EncryptedPositiveSmallIntegerField(queries={"queryType": "range"})


class SmallIntegerModel(EncryptedTestModel):
    value = EncryptedSmallIntegerField(queries={"queryType": "range"})


class TimeModel(EncryptedTestModel):
    value = EncryptedTimeField(queries={"queryType": "range"})
