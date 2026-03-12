from django.core import checks
from django.db.backends.base.validation import BaseDatabaseValidation


class DatabaseValidation(BaseDatabaseValidation):
    prohibited_fields = {"AutoField", "BigAutoField", "SmallAutoField"}

    def check_field_type(self, field, field_type):
        """Prohibit AutoField on MongoDB."""
        errors = []
        if field.get_internal_type() in self.prohibited_fields:
            errors.append(
                checks.Error(
                    f"{self.connection.display_name} does not support {field.__class__.__name__}.",
                    obj=field,
                    hint="Use django_mongodb_backend.fields.ObjectIdAutoField instead.",
                    id="mongodb.fields.auto.E001",
                )
            )
        return errors
