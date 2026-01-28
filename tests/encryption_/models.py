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


class EncryptedModel(models.Model):
    class Meta:
        abstract = True
        required_db_features = {"supports_queryable_encryption"}


# Array models
class ArrayModel(EncryptedModel):
    values = EncryptedArrayField(models.IntegerField(), size=5)


# Embedded models
class Patient(EncryptedModel):
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


class Movie(EncryptedModel):
    title = models.CharField(max_length=200)
    cast = EncryptedEmbeddedModelArrayField(Actor)

    def __str__(self):
        return self.title


# Equality-queryable models
class BinaryModel(EncryptedModel):
    value = EncryptedBinaryField(queries={"queryType": "equality"})


class BooleanModel(EncryptedModel):
    value = EncryptedBooleanField(queries={"queryType": "equality"})


class CharModel(EncryptedModel):
    value = EncryptedCharField(max_length=255, queries={"queryType": "equality"})


class EmailModel(EncryptedModel):
    value = EncryptedEmailField(max_length=255, queries={"queryType": "equality"})


class GenericIPAddressModel(EncryptedModel):
    value = EncryptedGenericIPAddressField(queries={"queryType": "equality"})


class ObjectIdModel(EncryptedModel):
    value = EncryptedObjectIdField(queries={"queryType": "equality"})


class TextModel(EncryptedModel):
    value = EncryptedTextField(queries={"queryType": "equality"})


class URLModel(EncryptedModel):
    value = EncryptedURLField(max_length=500, queries={"queryType": "equality"})


class UUIDModel(EncryptedModel):
    value = EncryptedUUIDField(queries={"queryType": "equality"})


# Range-queryable models
class BigIntegerModel(EncryptedModel):
    value = EncryptedBigIntegerField(queries={"queryType": "range"})


class DateModel(EncryptedModel):
    value = EncryptedDateField(queries={"queryType": "range"})


class DateTimeModel(EncryptedModel):
    value = EncryptedDateTimeField(queries={"queryType": "range"})


class DecimalModel(EncryptedModel):
    value = EncryptedDecimalField(max_digits=10, decimal_places=2, queries={"queryType": "range"})


class DurationModel(EncryptedModel):
    value = EncryptedDurationField(queries={"queryType": "range"})


class FloatModel(EncryptedModel):
    value = EncryptedFloatField(queries={"queryType": "range"})


class IntegerModel(EncryptedModel):
    value = EncryptedIntegerField(queries={"queryType": "range"})


class PositiveBigIntegerModel(EncryptedModel):
    value = EncryptedPositiveBigIntegerField(queries={"queryType": "range"})


class PositiveIntegerModel(EncryptedModel):
    value = EncryptedPositiveIntegerField(queries={"queryType": "range"})


class PositiveSmallIntegerModel(EncryptedModel):
    value = EncryptedPositiveSmallIntegerField(queries={"queryType": "range"})


class SmallIntegerModel(EncryptedModel):
    value = EncryptedSmallIntegerField(queries={"queryType": "range"})


class TimeModel(EncryptedModel):
    value = EncryptedTimeField(queries={"queryType": "range"})


# An unmanaged model for testing a model that doesn't have its encryption keys
# in the key vault.
class KeyTestModel(models.Model):
    value = EncryptedCharField(max_length=255)

    class Meta:
        managed = False


# Allow querying the key vault using the ORM
class EncryptionKey(models.Model):
    key_alt_name = models.CharField(max_length=500, db_column="keyAltNames")

    class Meta:
        db_table = "__keyVault"
        managed = False
