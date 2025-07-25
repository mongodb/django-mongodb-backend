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
    EncryptedFieldMixin,
    EncryptedFloatField,
    EncryptedGenericIPAddressField,
    EncryptedIntegerField,
    EncryptedTextField,
)
from django_mongodb_backend.models import EncryptedModel


class EncryptedDurationField(EncryptedFieldMixin, models.DurationField):
    """
    Unsupported by MongoDB when used with Queryable Encryption.
    Included in tests until fix or wontfix.
    """


class EncryptedSlugField(EncryptedFieldMixin, models.SlugField):
    """
    Unsupported by MongoDB when used with Queryable Encryption.
    Included in tests until fix or wontfix.
    """


class Appointment(EncryptedModel):
    duration = EncryptedDurationField("duration", queries=RangeQuery())


class Billing(EncryptedModel):
    cc_type = EncryptedCharField(max_length=20, queries=EqualityQuery())
    cc_number = EncryptedBigIntegerField(queries=EqualityQuery())
    account_balance = EncryptedDecimalField(max_digits=10, decimal_places=2, queries=RangeQuery())

    class Meta:
        db_table = "billing"


class PatientPortalUser(EncryptedModel):
    ip_address = EncryptedGenericIPAddressField(queries=EqualityQuery())


class PatientRecord(EncryptedModel):
    ssn = EncryptedCharField(max_length=11, queries=EqualityQuery())
    birth_date = EncryptedDateField(queries=RangeQuery())
    profile_picture = EncryptedBinaryField(queries=EqualityQuery())
    patient_age = EncryptedIntegerField("patient_age", queries=RangeQuery())
    weight = EncryptedFloatField(queries=RangeQuery())

    # TODO: Embed Billing model
    # billing =

    class Meta:
        db_table = "patientrecord"


class Patient(EncryptedModel):
    patient_id = EncryptedIntegerField("patient_id", queries=EqualityQuery())
    patient_name = EncryptedCharField(max_length=100)
    patient_notes = EncryptedTextField(queries=EqualityQuery())
    registration_date = EncryptedDateTimeField(queries=EqualityQuery())
    is_active = EncryptedBooleanField(queries=EqualityQuery())
    email = EncryptedEmailField(max_length=254, queries=EqualityQuery())

    # TODO: Embed PatientRecord model
    # patient_record =

    class Meta:
        db_table = "patient"
