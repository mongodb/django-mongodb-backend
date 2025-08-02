from django.db import models

from django_mongodb_backend.encryption import EqualityQuery, RangeQuery
from django_mongodb_backend.fields import (
    EncryptedBigIntegerField,
    EncryptedBinaryField,
    EncryptedBooleanField,
    EncryptedCharField,
    EncryptedDateField,
    EncryptedDateTimeField,
    EncryptedDecimalField,
    EncryptedEmailField,
    EncryptedFloatField,
    EncryptedGenericIPAddressField,
    EncryptedIntegerField,
    EncryptedPositiveBigIntegerField,
    EncryptedPositiveSmallIntegerField,
    EncryptedSmallIntegerField,
    EncryptedTextField,
    EncryptedTimeField,
    EncryptedURLField,
)


class Appointment(models.Model):
    time = EncryptedTimeField(queries=EqualityQuery())

    class Meta:
        required_db_features = {"supports_queryable_encryption"}


class Billing(models.Model):
    cc_type = EncryptedCharField(max_length=20, queries=EqualityQuery())
    cc_number = EncryptedBigIntegerField(queries=EqualityQuery())
    account_balance = EncryptedDecimalField(max_digits=10, decimal_places=2, queries=RangeQuery())

    class Meta:
        required_db_features = {"supports_queryable_encryption"}


class PatientPortalUser(models.Model):
    ip_address = EncryptedGenericIPAddressField(queries=EqualityQuery())
    url = EncryptedURLField(queries=EqualityQuery())

    class Meta:
        required_db_features = {"supports_queryable_encryption"}


class PatientRecord(models.Model):
    ssn = EncryptedCharField(max_length=11, queries=EqualityQuery())
    birth_date = EncryptedDateField(queries=RangeQuery())
    profile_picture = EncryptedBinaryField(queries=EqualityQuery())
    patient_age = EncryptedIntegerField("patient_age", queries=RangeQuery())
    weight = EncryptedFloatField(queries=RangeQuery())

    # TODO: Embed Billing model
    # billing =

    class Meta:
        required_db_features = {"supports_queryable_encryption"}


class Patient(models.Model):
    patient_id = EncryptedIntegerField("patient_id", queries=EqualityQuery())
    patient_name = EncryptedCharField(max_length=100)
    patient_notes = EncryptedTextField(queries=EqualityQuery())
    registration_date = EncryptedDateTimeField(queries=EqualityQuery())
    is_active = EncryptedBooleanField(queries=EqualityQuery())
    email = EncryptedEmailField(max_length=254, queries=EqualityQuery())

    # TODO: Embed PatientRecord model
    # patient_record =

    class Meta:
        required_db_features = {"supports_queryable_encryption"}


class EncryptedNumbers(models.Model):
    pos_bigint = EncryptedPositiveBigIntegerField(queries=EqualityQuery())

    # FIXME: pymongo.errors.EncryptionError: Cannot encrypt element of type int
    # because schema requires that type is one of: [ long ]
    # pos_int = EncryptedPositiveIntegerField(queries=EqualityQuery())

    pos_smallint = EncryptedPositiveSmallIntegerField(queries=EqualityQuery())
    smallint = EncryptedSmallIntegerField(queries=EqualityQuery())
