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

EQUALITY_QUERY = {"queryType": "equality"}
RANGE_QUERY = {"queryType": "range"}


class QueryableEncryptionModelBase(models.Model):
    class Meta:
        abstract = True
        required_db_features = {"supports_queryable_encryption"}


class Appointment(QueryableEncryptionModelBase):
    start_time = EncryptedTimeField(queries=EQUALITY_QUERY)


class Billing(QueryableEncryptionModelBase):
    account_balance = EncryptedDecimalField(max_digits=10, decimal_places=2, queries=RANGE_QUERY)
    payment_duration = EncryptedDurationField(queries=RANGE_QUERY)  # Duration for billing period


class CreditCard(QueryableEncryptionModelBase):
    card_type = EncryptedCharField(max_length=20, queries=EQUALITY_QUERY)
    card_number = EncryptedIntegerField(queries=EQUALITY_QUERY)
    transaction_reference = EncryptedBigIntegerField(
        queries=EQUALITY_QUERY
    )  # Simulating a long transaction ID


class PatientPortalUser(QueryableEncryptionModelBase):
    last_login_ip = EncryptedGenericIPAddressField(queries=EQUALITY_QUERY)
    profile_url = EncryptedURLField(queries=EQUALITY_QUERY)


class PatientRecord(QueryableEncryptionModelBase):
    ssn = EncryptedCharField(max_length=11, queries=EQUALITY_QUERY)
    birth_date = EncryptedDateField(queries=RANGE_QUERY)
    profile_picture_data = EncryptedBinaryField(queries=EQUALITY_QUERY)
    age = EncryptedSmallIntegerField(queries={**RANGE_QUERY, "min": 0, "max": 100})
    weight = EncryptedFloatField(queries=RANGE_QUERY)
    insurance_policy_number = EncryptedPositiveBigIntegerField(queries=EQUALITY_QUERY)
    emergency_contacts_count = EncryptedPositiveIntegerField(queries=EQUALITY_QUERY)
    completed_visits = EncryptedPositiveSmallIntegerField(queries=EQUALITY_QUERY)

    # TODO: Embed Billing model
    # billing = EncryptedEmbeddedField(Billing)


class Patient(QueryableEncryptionModelBase):
    patient_id = EncryptedIntegerField(queries=EQUALITY_QUERY)
    full_name = EncryptedCharField(max_length=100)
    notes = EncryptedTextField(queries=EQUALITY_QUERY)
    registration_date = EncryptedDateTimeField(queries=EQUALITY_QUERY)
    is_active = EncryptedBooleanField(queries=EQUALITY_QUERY)
    contact_email = EncryptedEmailField(queries=EQUALITY_QUERY)

    # TODO: Embed PatientRecord model
    # patient_record = EncryptedEmbeddedField(PatientRecord)
