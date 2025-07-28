import contextlib

from django.core import checks
from django.core.exceptions import FieldDoesNotExist, ValidationError
from django.db import models
from django.db.models.fields.related import lazy_related_operation

from .embedded_model import KeyTransformFactory
from .utils import get_mongodb_connection


class PolymorphicEmbeddedModelField(models.Field):
    """Field that stores a model instance of varying type."""

    stores_model_instance = True

    def __init__(self, embedded_models, *args, **kwargs):
        """
        `embedded_models` is a list of possible model classes to be stored.
        Like other relational fields, each model may also be passed as a
        string.
        """
        self.embedded_models = embedded_models
        kwargs["editable"] = False
        super().__init__(*args, **kwargs)

    def db_type(self, connection):
        return "embeddedDocuments"

    def check(self, **kwargs):
        from ..models import EmbeddedModel  # noqa: PLC0415

        errors = super().check(**kwargs)
        embedded_fields = {}
        for model in self.embedded_models:
            if not issubclass(model, EmbeddedModel):
                return [
                    checks.Error(
                        "Embedded models must be a subclass of "
                        "django_mongodb_backend.models.EmbeddedModel.",
                        obj=self,
                        hint="{model} doesn't subclass EmbeddedModel.",
                        id="django_mongodb_backend.embedded_model.E002",
                    )
                ]
            for field in model._meta.fields:
                if field.remote_field:
                    errors.append(
                        checks.Error(
                            "Embedded models cannot have relational fields "
                            f"({model().__class__.__name__}.{field.name} "
                            f"is a {field.__class__.__name__}).",
                            obj=self,
                            id="django_mongodb_backend.embedded_model.E001",
                        )
                    )
                field_name = field.name
                if existing_field := embedded_fields.get(field.name):
                    connection = get_mongodb_connection()
                    if existing_field.db_type(connection) != field.db_type(connection):
                        errors.append(
                            checks.Warning(
                                f"Embedded models {existing_field.model._meta.label} "
                                f"and {field.model._meta.label} both have field "
                                f"'{field_name}' of different type.",
                                obj=self,
                                id="django_mongodb_backend.embedded_model.E003",
                                hint="It may be impossible to query both fields.",
                            )
                        )

                else:
                    embedded_fields[field_name] = field
        return errors

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        if path.startswith("django_mongodb_backend.fields.polymorphic_embedded_model"):
            path = path.replace(
                "django_mongodb_backend.fields.polymorphic_embedded_model",
                "django_mongodb_backend.fields",
            )
        kwargs["embedded_models"] = self.embedded_models
        del kwargs["editable"]
        return name, path, args, kwargs

    def get_internal_type(self):
        return "PolymorphicEmbeddedModelField"

    def _set_model(self, model):
        """
        Resolve embedded model classes once the field knows the model it
        belongs to. If any of the items in __init__()'s embedded_models
        argument are strings, resolve each to the actual model class, similar
        to relational fields.
        """
        self._model = model
        if model is not None:
            for embedded_model in self.embedded_models:
                if isinstance(embedded_model, str):

                    def _resolve_lookup(_, *resolved_models):
                        self.embedded_models = resolved_models

                    lazy_related_operation(_resolve_lookup, model, *self.embedded_models)

    model = property(lambda self: self._model, _set_model)

    def from_db_value(self, value, expression, connection):
        return self.to_python(value)

    def to_python(self, value):
        """
        Pass embedded model fields' values through each field's to_python() and
        reinstantiate the embedded instance.
        """
        if value is None:
            return None
        if not isinstance(value, dict):
            return value
        model_class = self._get_model_from_label(value.pop("_label"))
        instance = model_class(
            **{
                field.attname: field.to_python(value[field.attname])
                for field in model_class._meta.fields
                if field.attname in value
            }
        )
        instance._state.adding = False
        return instance

    def get_db_prep_save(self, embedded_instance, connection):
        """
        Apply pre_save() and get_db_prep_save() of embedded instance fields and
        create the {field: value} dict to be saved.
        """
        if embedded_instance is None:
            return None
        if not isinstance(embedded_instance, self.embedded_models):
            raise TypeError(
                f"Expected instance of type {self.embedded_models!r}, not "
                f"{type(embedded_instance)!r}."
            )
        field_values = {}
        add = embedded_instance._state.adding
        for field in embedded_instance._meta.fields:
            value = field.get_db_prep_save(
                field.pre_save(embedded_instance, add), connection=connection
            )
            # Exclude unset primary keys (e.g. {'id': None}).
            if field.primary_key and value is None:
                continue
            field_values[field.attname] = value
        # Store the model's label to know the class to use for initializing
        # upon retrieval.
        field_values["_label"] = embedded_instance._meta.label
        # This instance will exist in the database soon.
        embedded_instance._state.adding = False
        return field_values

    def get_transform(self, name):
        transform = super().get_transform(name)
        if transform:
            return transform
        for model in self.embedded_models:
            with contextlib.suppress(FieldDoesNotExist):
                field = model._meta.get_field(name)
                break
        else:
            raise FieldDoesNotExist(
                f"The models of field '{self.name}' have no field named '{name}'."
            )
        return KeyTransformFactory(name, field)

    def validate(self, value, model_instance):
        super().validate(value, model_instance)
        if not isinstance(value, self.embedded_models):
            raise ValidationError(
                f"Expected instance of type {self.embedded_models!r}, not {type(value)!r}."
            )
        for field in value._meta.fields:
            attname = field.attname
            field.validate(getattr(value, attname), model_instance)

    def formfield(self, **kwargs):
        raise NotImplementedError("PolymorphicEmbeddedModelField does not support forms.")

    def _get_model_from_label(self, label):
        return next(model for model in self.embedded_models if model._meta.label == label)
