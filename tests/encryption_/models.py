from django_mongodb_backend.encryption import QueryType
from django_mongodb_backend.fields import EncryptedCharField, EncryptedIntegerField
from django_mongodb_backend.models import EncryptedModel


class Billing(EncryptedModel):
    class Meta:
        db_table = "billing"

    cc_type = EncryptedCharField("cc_type", max_length=20, queries=QueryType.equality())
    cc_number = EncryptedIntegerField("cc_number", queries=QueryType.equality())


class PatientRecord(EncryptedModel):
    class Meta:
        db_table = "patient_record"

    ssn = EncryptedCharField("ssn", max_length=11, queries=QueryType.equality())

    # TODO: Embed Billing model
    # billing =


class Patient(EncryptedModel):
    class Meta:
        db_table = "patient"

    patient_id = EncryptedIntegerField("patient_id")
    patient_age = EncryptedIntegerField("patient_age", queries=QueryType.range())
    patient_name = EncryptedCharField("name", max_length=100)

    # TODO: Embed PatientRecord model
    # patient_record =
