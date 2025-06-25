from django.db import models


class EncryptedFieldMixin(models.Field):
    encrypted = True

    def __init__(self, *args, queries=None, **kwargs):
        self.queries = queries
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()

        if self.queries is not None:
            kwargs["queries"] = self.queries

        if path.startswith("django_mongodb_backend.fields.encrypted_model"):
            path = path.replace(
                "django_mongodb_backend.fields.encrypted_model",
                "django_mongodb_backend.fields",
            )

        return name, path, args, kwargs


class EncryptedBigIntegerField(EncryptedFieldMixin, models.BigIntegerField):
    pass


class EncryptedBinaryField(EncryptedFieldMixin, models.BinaryField):
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


class EncryptedTimeField(EncryptedFieldMixin, models.TimeField):
    pass


class EncryptedTextField(EncryptedFieldMixin, models.TextField):
    pass


class EncryptedURLField(EncryptedFieldMixin, models.URLField):
    pass
