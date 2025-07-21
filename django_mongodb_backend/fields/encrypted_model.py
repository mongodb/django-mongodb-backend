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

        if path.startswith("django_mongodb_backend.fields.encryption"):
            path = path.replace(
                "django_mongodb_backend.fields.encryption",
                "django_mongodb_backend.fields",
            )

        return name, path, args, kwargs


class EncryptedCharField(EncryptedFieldMixin, models.CharField):
    pass


class EncryptedIntegerField(EncryptedFieldMixin, models.IntegerField):
    pass


class EncryptedBigIntegerField(EncryptedFieldMixin, models.BigIntegerField):
    pass
