from django.db import models

from django_mongodb_backend.fields import (
    EmbeddedModelField,
    EncryptedArrayField,
    EncryptedBigIntegerField,
    EncryptedBinaryField,
    EncryptedBooleanField,
    EncryptedCharField,
    EncryptedDateField,
    EncryptedDateTimeField,
    EncryptedDecimalField,
    EncryptedDurationField,
    EncryptedEmailField,
    EncryptedEmbeddedModelArrayField,
    EncryptedEmbeddedModelField,
    EncryptedFloatField,
    EncryptedGenericIPAddressField,
    EncryptedIntegerField,
    EncryptedObjectIdField,
    EncryptedPositiveBigIntegerField,
    EncryptedPositiveIntegerField,
    EncryptedPositiveSmallIntegerField,
    EncryptedSmallIntegerField,
    EncryptedTextField,
    EncryptedTimeField,
    EncryptedURLField,
    EncryptedUUIDField,
)
from django_mongodb_backend.models import EmbeddedModel


class Author(models.Model):
    name = models.CharField(max_length=255)


class Book(models.Model):
    title = models.CharField(max_length=255)
    author = models.ForeignKey(Author, models.CASCADE)


class EncryptedTestModel(models.Model):
    class Meta:
        abstract = True
        required_db_features = {"supports_queryable_encryption"}


# Array models
class ArrayModel(EncryptedTestModel):
    values = EncryptedArrayField(
        models.IntegerField(),
        size=5,
    )


# Embedded models
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


# Embedded array models
class Actor(EmbeddedModel):
    name = models.CharField(max_length=100)


class Movie(EncryptedTestModel):
    title = models.CharField(max_length=200)
    plot = models.TextField(blank=True)
    runtime = models.IntegerField(default=0)
    released = models.DateTimeField("release date")
    cast = EncryptedEmbeddedModelArrayField(Actor)

    def __str__(self):
        return self.title


# Equality-queryable field models
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


class ObjectIdModel(EncryptedTestModel):
    value = EncryptedObjectIdField(queries={"queryType": "equality"})


class TextModel(EncryptedTestModel):
    value = EncryptedTextField(queries={"queryType": "equality"})


class URLModel(EncryptedTestModel):
    value = EncryptedURLField(max_length=500, queries={"queryType": "equality"})


class UUIDModel(EncryptedTestModel):
    value = EncryptedUUIDField(queries={"queryType": "equality"})


# Range-queryable field models
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


class EncryptionKey(models.Model):
    key_alt_name = models.CharField(max_length=500, db_column="keyAltNames")

    class Meta:
        db_table = "__keyVault"
        managed = False
