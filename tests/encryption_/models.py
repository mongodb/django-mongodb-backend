from django_mongodb_backend.encryption import QueryType
from django_mongodb_backend.fields import (
    EncryptedBigIntegerField,
    EncryptedBinaryField,
    EncryptedBooleanField,
    EncryptedCharField,
    EncryptedDateField,
    EncryptedDateTimeField,
    EncryptedDecimalField,
    EncryptedFloatField,
    EncryptedIntegerField,
    EncryptedTextField,
)
from django_mongodb_backend.models import EncryptedModel


class Billing(EncryptedModel):
    cc_type = EncryptedCharField(max_length=20, queries=QueryType.equality())
    cc_number = EncryptedBigIntegerField(queries=QueryType.equality())
    account_balance = EncryptedDecimalField(
        max_digits=10, decimal_places=2, queries=QueryType.range()
    )

    class Meta:
        db_table = "billing"


class PatientRecord(EncryptedModel):
    ssn = EncryptedCharField(max_length=11, queries=QueryType.equality())
    birth_date = EncryptedDateField(queries=QueryType.range())
    profile_picture = EncryptedBinaryField(queries=QueryType.equality())
    patient_age = EncryptedIntegerField("patient_age", queries=QueryType.range())
    weight = EncryptedFloatField(queries=QueryType.range())

    # TODO: Embed Billing model
    # billing =

    class Meta:
        db_table = "patientrecord"


class Patient(EncryptedModel):
    patient_id = EncryptedIntegerField("patient_id", queries=QueryType.equality())
    patient_name = EncryptedCharField(max_length=100)
    patient_notes = EncryptedTextField(queries=QueryType.equality())
    registration_date = EncryptedDateTimeField(queries=QueryType.equality())
    is_active = EncryptedBooleanField(queries=QueryType.equality())

    # TODO: Embed PatientRecord model
    # patient_record =

    class Meta:
        db_table = "patient"
