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
class EncryptedBinaryTest(EncryptedTestModel):
    value = EncryptedBinaryField(queries={"queryType": "equality"})


class EncryptedBooleanTest(EncryptedTestModel):
    value = EncryptedBooleanField(queries={"queryType": "equality"})


class EncryptedCharTest(EncryptedTestModel):
    value = EncryptedCharField(max_length=255, queries={"queryType": "equality"})


class EncryptedEmailTest(EncryptedTestModel):
    value = EncryptedEmailField(max_length=255, queries={"queryType": "equality"})


class EncryptedGenericIPAddressTest(EncryptedTestModel):
    value = EncryptedGenericIPAddressField(queries={"queryType": "equality"})


class EncryptedTextTest(EncryptedTestModel):
    value = EncryptedTextField(queries={"queryType": "equality"})


class EncryptedURLTest(EncryptedTestModel):
    value = EncryptedURLField(max_length=500, queries={"queryType": "equality"})


# Range-queryable fields (also support equality)
class EncryptedBigIntegerTest(EncryptedTestModel):
    value = EncryptedBigIntegerField(queries={"queryType": "range"})


class EncryptedDateTest(EncryptedTestModel):
    value = EncryptedDateField(queries={"queryType": "range"})


class EncryptedDateTimeTest(EncryptedTestModel):
    value = EncryptedDateTimeField(queries={"queryType": "range"})


class EncryptedDecimalTest(EncryptedTestModel):
    value = EncryptedDecimalField(max_digits=10, decimal_places=2, queries={"queryType": "range"})


class EncryptedDurationTest(EncryptedTestModel):
    value = EncryptedDurationField(queries={"queryType": "range"})


class EncryptedFloatTest(EncryptedTestModel):
    value = EncryptedFloatField(queries={"queryType": "range"})


class EncryptedIntegerTest(EncryptedTestModel):
    value = EncryptedIntegerField(queries={"queryType": "range"})


class EncryptedPositiveBigIntegerTest(EncryptedTestModel):
    value = EncryptedPositiveBigIntegerField(queries={"queryType": "range"})


class EncryptedPositiveIntegerTest(EncryptedTestModel):
    value = EncryptedPositiveIntegerField(queries={"queryType": "range"})


class EncryptedPositiveSmallIntegerTest(EncryptedTestModel):
    value = EncryptedPositiveSmallIntegerField(queries={"queryType": "range"})


class EncryptedSmallIntegerTest(EncryptedTestModel):
    value = EncryptedSmallIntegerField(queries={"queryType": "range"})


class EncryptedTimeTest(EncryptedTestModel):
    value = EncryptedTimeField(queries={"queryType": "range"})
