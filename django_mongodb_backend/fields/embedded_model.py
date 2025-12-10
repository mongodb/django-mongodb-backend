import difflib

from django.core import checks
from django.core.exceptions import FieldDoesNotExist, ValidationError
from django.db import models
from django.db.models.fields.related import lazy_related_operation
from django.db.models.lookups import Transform
from django.utils.functional import cached_property

from django_mongodb_backend import forms


class EmbeddedModelField(models.Field):
    """Field that stores a model instance."""

    stores_model_instance = True

    def __init__(self, embedded_model, *args, **kwargs):
        """
        `embedded_model` is the model class of the instance to be stored.
        Like other relational fields, it may also be passed as a string.
        """
        self.embedded_model = embedded_model
        super().__init__(*args, **kwargs)

    def db_type(self, connection):
        return "object"

    def check(self, **kwargs):
        from django_mongodb_backend.models import EmbeddedModel  # noqa: PLC0415

        errors = super().check(**kwargs)
        if not issubclass(self.embedded_model, EmbeddedModel):
            return [
                checks.Error(
                    "Embedded models must be a subclass of "
                    "django_mongodb_backend.models.EmbeddedModel.",
                    obj=self,
                    id="django_mongodb_backend.embedded_model.E002",
                )
            ]
        for field in self.embedded_model._meta.fields:
            if field.remote_field:
                errors.append(
                    checks.Error(
                        "Embedded models cannot have relational fields "
                        f"({self.embedded_model().__class__.__name__}.{field.name} "
                        f"is a {field.__class__.__name__}).",
                        obj=self,
                        id="django_mongodb_backend.embedded_model.E001",
                    )
                )
        return errors

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        if path.startswith("django_mongodb_backend.fields.embedded_model"):
            path = path.replace(
                "django_mongodb_backend.fields.embedded_model", "django_mongodb_backend.fields"
            )
        kwargs["embedded_model"] = self.embedded_model
        return name, path, args, kwargs

    def get_internal_type(self):
        return "EmbeddedModelField"

    def _set_model(self, model):
        """
        Resolve embedded model class once the field knows the model it belongs
        to. If __init__()'s embedded_model argument is a string, resolve it to
        the actual model class, similar to relation fields.
        """
        self._model = model
        if model is not None and isinstance(self.embedded_model, str):

            def _resolve_lookup(_, resolved_model):
                self.embedded_model = resolved_model

            lazy_related_operation(_resolve_lookup, model, self.embedded_model)

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
        instance = self.embedded_model(
            **{
                field.attname: field.to_python(value[field.column])
                for field in self.embedded_model._meta.fields
                if field.column in value
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
        if not isinstance(embedded_instance, self.embedded_model):
            raise TypeError(
                f"Expected instance of type {self.embedded_model!r}, not "
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
            field_values[field.column] = value
        # This instance will exist in the database soon.
        embedded_instance._state.adding = False
        return field_values

    def get_transform(self, name):
        transform = super().get_transform(name)
        if transform:
            return transform
        field = self.embedded_model._meta.get_field(name)
        return EmbeddedModelTransformFactory(field)

    def validate(self, value, model_instance):
        super().validate(value, model_instance)
        if not isinstance(value, self.embedded_model):
            raise ValidationError(
                f"Expected instance of type {self.embedded_model!r}, not {type(value)!r}."
            )

        for field in self.embedded_model._meta.fields:
            attname = field.attname
            field.validate(getattr(value, attname), model_instance)

    def formfield(self, **kwargs):
        return super().formfield(
            **{
                "form_class": forms.EmbeddedModelField,
                "model": self.embedded_model,
                "prefix": self.name,
                **kwargs,
            }
        )


class EmbeddedModelTransform(Transform):
    def __init__(self, field, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # self.field aliases self._field via BaseExpression.field returning
        # self.output_field.
        self._field = field

    def get_lookup(self, name):
        return self.field.get_lookup(name)

    def get_transform(self, name):
        """
        Validate that `name` is either a field of an embedded model or a
        lookup on an embedded model's field.
        """
        if transform := self.field.get_transform(name):
            return transform
        suggested_lookups = difflib.get_close_matches(name, self.field.get_lookups())
        if suggested_lookups:
            suggested_lookups = " or ".join(suggested_lookups)
            suggestion = f", perhaps you meant {suggested_lookups}?"
        else:
            suggestion = "."
        raise FieldDoesNotExist(
            f"Unsupported lookup '{name}' for "
            f"{self.field.__class__.__name__} '{self.field.name}'"
            f"{suggestion}"
        )

    def _get_target_path(self):
        previous = self
        columns = []
        while isinstance(previous, EmbeddedModelTransform):
            columns.insert(0, previous.field.column)
            previous = previous.lhs
        return columns, previous

    def as_mql_expr(self, compiler, connection):
        columns, parent_field = self._get_target_path()
        mql = parent_field.as_mql(compiler, connection, as_expr=True)
        for column in columns:
            mql = {"$getField": {"input": mql, "field": column}}
        return mql

    def as_mql_path(self, compiler, connection):
        columns, parent_field = self._get_target_path()
        mql = parent_field.as_mql(compiler, connection)
        mql_path = ".".join(columns)
        return f"{mql}.{mql_path}"

    @property
    def output_field(self):
        return self._field

    @property
    def can_use_path(self):
        return self.is_simple_column

    @cached_property
    def is_simple_column(self):
        previous = self
        while isinstance(previous, EmbeddedModelTransform):
            previous = previous.lhs
        return previous.is_simple_column


class EmbeddedModelTransformFactory:
    def __init__(self, field):
        self.field = field

    def __call__(self, *args, **kwargs):
        return EmbeddedModelTransform(self.field, *args, **kwargs)
