from django.db import models

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

EQUALITY_QUERY = {"queryType": "equality"}
RANGE_QUERY = {"queryType": "range"}
RANGE_QUERY_MIN_MAX = {"queryType": "range", "min": 0, "max": 100}


class Appointment(models.Model):
    time = EncryptedTimeField(queries=EQUALITY_QUERY)

    class Meta:
        required_db_features = {"supports_queryable_encryption"}


class Billing(models.Model):
    cc_type = EncryptedCharField(max_length=20, queries=EQUALITY_QUERY)
    cc_number = EncryptedBigIntegerField(queries=EQUALITY_QUERY)
    account_balance = EncryptedDecimalField(max_digits=10, decimal_places=2, queries=RANGE_QUERY)

    class Meta:
        required_db_features = {"supports_queryable_encryption"}


class PatientPortalUser(models.Model):
    ip_address = EncryptedGenericIPAddressField(queries=EQUALITY_QUERY)
    url = EncryptedURLField(queries=EQUALITY_QUERY)

    class Meta:
        required_db_features = {"supports_queryable_encryption"}


class PatientRecord(models.Model):
    ssn = EncryptedCharField(max_length=11, queries=EQUALITY_QUERY)
    birth_date = EncryptedDateField(queries=RANGE_QUERY)
    profile_picture = EncryptedBinaryField(queries=EQUALITY_QUERY)
    patient_age = EncryptedIntegerField("patient_age", queries=RANGE_QUERY_MIN_MAX)
    weight = EncryptedFloatField(queries=RANGE_QUERY)

    # TODO: Embed Billing model
    # billing =

    class Meta:
        required_db_features = {"supports_queryable_encryption"}


class Patient(models.Model):
    patient_id = EncryptedIntegerField("patient_id", queries=EQUALITY_QUERY)
    patient_name = EncryptedCharField(max_length=100)
    patient_notes = EncryptedTextField(queries=EQUALITY_QUERY)
    registration_date = EncryptedDateTimeField(queries=EQUALITY_QUERY)
    is_active = EncryptedBooleanField(queries=EQUALITY_QUERY)
    email = EncryptedEmailField(queries=EQUALITY_QUERY)

    # TODO: Embed PatientRecord model
    # patient_record =

    class Meta:
        required_db_features = {"supports_queryable_encryption"}


class EncryptedNumbers(models.Model):
    pos_bigint = EncryptedPositiveBigIntegerField(queries=EQUALITY_QUERY)

    # FIXME: pymongo.errors.EncryptionError: Cannot encrypt element of type int
    # because schema requires that type is one of: [ long ]
    # pos_int = EncryptedPositiveIntegerField(queries=EQUALITY_QUERY)

    pos_smallint = EncryptedPositiveSmallIntegerField(queries=EQUALITY_QUERY)
    smallint = EncryptedSmallIntegerField(queries=EQUALITY_QUERY)
