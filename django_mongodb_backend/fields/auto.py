from django.db.models.fields import AutoField
from django.utils.functional import cached_property

from .objectid import ObjectIdMixin


class ObjectIdAutoField(ObjectIdMixin, AutoField):
    def __init__(self, *args, **kwargs):
        kwargs["db_column"] = "_id"
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        if self.db_column == "_id":
            del kwargs["db_column"]
        if path.startswith("django_mongodb_backend.fields.auto"):
            path = path.replace(
                "django_mongodb_backend.fields.auto", "django_mongodb_backend.fields"
            )
        return name, path, args, kwargs

    def get_prep_value(self, value):
        # Override to omit super() which would call AutoField/IntegerField's
        # implementation that requires value to be an integer.
        return self.to_python(value)

    def get_internal_type(self):
        return "ObjectIdAutoField"

    @cached_property
    def validators(self):
        # Avoid IntegerField validators inherited from AutoField.
        return [*self.default_validators, *self._validators]
