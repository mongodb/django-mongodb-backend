from django.core import checks
from django.db import NotSupportedError, models

from .managers import EmbeddedModelManager


class EmbeddedModel(models.Model):
    objects = EmbeddedModelManager()

    class Meta:
        abstract = True

    @classmethod
    def check(self, **kwargs):
        errors = super().check(**kwargs)
        for field in self._meta.fields:
            # Ignore auto-created primary keys.
            if field.auto_created:
                continue
            if field.db_index:
                errors.append(
                    checks.Warning(
                        "Using db_index=True on embedded fields is deprecated "
                        "in favor of using EmbeddedFieldIndex in Meta.indexes "
                        "on the top-level model.",
                        obj=field,
                        id="mongodb.fields.embedded_model.W004",
                    )
                )
            if field.unique:
                errors.append(
                    checks.Warning(
                        "Using unique=True on embedded fields is deprecated "
                        "in favor of using EmbeddedFieldUniqueConstraint in "
                        "Meta.constraints on the top-level model.",
                        obj=field,
                        id="mongodb.fields.embedded_model.W005",
                    )
                )
        if self._meta.constraints:
            errors.append(
                checks.Warning(
                    "Using Meta.constraints on embedded models is deprecated "
                    "in favor of using EmbeddedFieldUniqueConstraint in "
                    "Meta.constraints on the top-level model.",
                    obj=self,
                    id="mongodb.fields.embedded_model.W006",
                )
            )
        if self._meta.indexes:
            errors.append(
                checks.Warning(
                    "Using Meta.indexes on embedded models is deprecated in "
                    "favor of using EmbeddedFieldIndex in Meta.indexes on the "
                    "top-level model.",
                    obj=self,
                    id="mongodb.fields.embedded_model.W007",
                )
            )
        if self._meta.unique_together:
            errors.append(
                checks.Warning(
                    "Using Meta.unique_together on embedded models is "
                    "deprecated in favor of using EmbeddedFieldUniqueConstraint "
                    "in Meta.constraints on the top-level model.",
                    obj=self,
                    id="mongodb.fields.embedded_model.W008",
                )
            )
        return errors

    def delete(self, *args, **kwargs):
        raise NotSupportedError("EmbeddedModels cannot be deleted.")

    def save(self, *args, **kwargs):
        raise NotSupportedError("EmbeddedModels cannot be saved.")
