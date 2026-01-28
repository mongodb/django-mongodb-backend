"""Mixins used across multiple modules (to avoid circular imports)."""

from django.core.checks import Error


class NoEncryptedEmbeddedFieldsMixin:
    def check(self, **kwargs):
        return [
            *super().check(**kwargs),
            *self._check_no_encrypted_fields(),
        ]

    def _check_no_encrypted_fields(self):
        for field in self.embedded_model._meta.fields:
            if getattr(field, "encrypted", False):
                return [
                    Error(
                        f"{self.__class__.__name__} cannot contain encrypted "
                        f"fields (found {field.__class__.__name__}).",
                        obj=self,
                        id="django_mongodb_backend.embedded_model_array.E001",
                    )
                ]
        return []
