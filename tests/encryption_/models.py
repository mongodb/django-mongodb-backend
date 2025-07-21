from django_mongodb_backend.encryption import QueryType
from django_mongodb_backend.fields import (
    EncryptedBigIntegerField,
    EncryptedCharField,
    EncryptedIntegerField,
    EncryptedTextField,
)
from django_mongodb_backend.models import EncryptedModel


class Billing(EncryptedModel):
    cc_type = EncryptedCharField(max_length=20, queries=QueryType.equality())
    cc_number = EncryptedBigIntegerField(queries=QueryType.equality())

    class Meta:
        db_table = "billing"


class PatientRecord(EncryptedModel):
    ssn = EncryptedCharField(max_length=11, queries=QueryType.equality())
    notes = EncryptedTextField(queries=QueryType.equality())

    # TODO: Embed Billing model
    # billing =

    class Meta:
        db_table = "patientrecord"


class Patient(EncryptedModel):
    patient_age = EncryptedIntegerField("patient_age", queries=QueryType.range())
    patient_id = EncryptedIntegerField("patient_id")
    patient_name = EncryptedCharField(max_length=100)

    # TODO: Embed PatientRecord model
    # patient_record =

    class Meta:
        db_table = "patient"
