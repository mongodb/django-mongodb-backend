from django.db import models

from django_mongodb_backend.fields import (
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
    EncryptedPositiveSmallIntegerField,
    EncryptedSmallIntegerField,
    EncryptedTextField,
    EncryptedTimeField,
    EncryptedURLField,
)

EQUALITY_QUERY = {"queryType": "equality"}
RANGE_QUERY = {"queryType": "range"}


class Appointment(models.Model):
    time = EncryptedTimeField(queries=EQUALITY_QUERY)

    class Meta:
        required_db_features = {"supports_queryable_encryption"}


class Billing(models.Model):
    cc_type = EncryptedCharField(max_length=20, queries=EQUALITY_QUERY)
    cc_number = EncryptedIntegerField(queries=EQUALITY_QUERY)
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
    patient_age = EncryptedSmallIntegerField(queries={**RANGE_QUERY, "min": 0, "max": 100})
    weight = EncryptedFloatField(queries=RANGE_QUERY)

    # TODO: Embed Billing model
    # billing =

    class Meta:
        required_db_features = {"supports_queryable_encryption"}


class Patient(models.Model):
    patient_id = EncryptedIntegerField(queries=EQUALITY_QUERY)
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
    # Not tested elsewhere
    pos_smallint = EncryptedPositiveSmallIntegerField(queries=EQUALITY_QUERY)
    smallint = EncryptedSmallIntegerField(queries=EQUALITY_QUERY)

    class Meta:
        required_db_features = {"supports_queryable_encryption"}


class SensitiveData(models.Model):
    # Example from documentation
    name = EncryptedCharField(max_length=100)
    email = EncryptedEmailField()
    phone_number = EncryptedCharField(max_length=15)

    sensitive_text = EncryptedTextField()
    sensitive_integer = EncryptedIntegerField()
    sensitive_date = EncryptedDateField()
