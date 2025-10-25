from django.db import models

from django_mongodb_backend.fields import ArrayField, EmbeddedModelArrayField, EmbeddedModelField
from django_mongodb_backend.fields.objectid import ObjectIdField


class EncryptedFieldMixin:
    encrypted = True

    def __init__(self, *args, queries=None, db_index=False, null=False, unique=False, **kwargs):
        if db_index:
            raise ValueError("'db_index=True' is not supported on encrypted fields.")
        if null:
            raise ValueError("'null=True' is not supported on encrypted fields.")
        if unique:
            raise ValueError("'unique=True' is not supported on encrypted fields.")
        self.queries = queries
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()

        if self.queries is not None:
            kwargs["queries"] = self.queries

        if path.startswith("django_mongodb_backend.fields.encryption"):
            path = path.replace(
                "django_mongodb_backend.fields.encryption",
                "django_mongodb_backend.fields",
            )

        return name, path, args, kwargs


# Django fields
class EncryptedBinaryField(EncryptedFieldMixin, models.BinaryField):
    pass


class EncryptedBigIntegerField(EncryptedFieldMixin, models.BigIntegerField):
    pass


class EncryptedBooleanField(EncryptedFieldMixin, models.BooleanField):
    pass


class EncryptedCharField(EncryptedFieldMixin, models.CharField):
    pass


class EncryptedDateField(EncryptedFieldMixin, models.DateField):
    pass


class EncryptedDateTimeField(EncryptedFieldMixin, models.DateTimeField):
    pass


class EncryptedDecimalField(EncryptedFieldMixin, models.DecimalField):
    pass


class EncryptedDurationField(EncryptedFieldMixin, models.DurationField):
    pass


class EncryptedEmailField(EncryptedFieldMixin, models.EmailField):
    pass


class EncryptedFloatField(EncryptedFieldMixin, models.FloatField):
    pass


class EncryptedGenericIPAddressField(EncryptedFieldMixin, models.GenericIPAddressField):
    pass


class EncryptedIntegerField(EncryptedFieldMixin, models.IntegerField):
    pass


class EncryptedPositiveBigIntegerField(EncryptedFieldMixin, models.PositiveBigIntegerField):
    pass


class EncryptedPositiveIntegerField(EncryptedFieldMixin, models.PositiveIntegerField):
    pass


class EncryptedPositiveSmallIntegerField(EncryptedFieldMixin, models.PositiveSmallIntegerField):
    pass


class EncryptedSmallIntegerField(EncryptedFieldMixin, models.SmallIntegerField):
    pass


class EncryptedTextField(EncryptedFieldMixin, models.TextField):
    pass


class EncryptedTimeField(EncryptedFieldMixin, models.TimeField):
    pass


class EncryptedURLField(EncryptedFieldMixin, models.URLField):
    pass


class EncryptedUUIDField(EncryptedFieldMixin, models.UUIDField):
    pass


# MongoDB fields
class EncryptedArrayField(EncryptedFieldMixin, ArrayField):
    pass


class EncryptedEmbeddedModelArrayField(EncryptedFieldMixin, EmbeddedModelArrayField):
    pass


class EncryptedEmbeddedModelField(EncryptedFieldMixin, EmbeddedModelField):
    pass


class EncryptedObjectIdField(EncryptedFieldMixin, ObjectIdField):
    pass
