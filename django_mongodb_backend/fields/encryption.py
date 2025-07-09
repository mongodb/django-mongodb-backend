from django.db import models


class EncryptedCharField(models.CharField):
    """Field that encrypts its value before saving to the database."""

    encrypted = True

    def __init__(self, *args, queries=None, **kwargs):
        self.queries = queries
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()

        # Add 'queries' to kwargs if it was set
        if self.queries is not None:
            kwargs["queries"] = self.queries

        # Normalize path if needed
        if path.startswith("django_mongodb_backend.fields.encryption"):
            path = path.replace(
                "django_mongodb_backend.fields.encryption",
                "django_mongodb_backend.fields",
            )

        return name, path, args, kwargs
