import json

from django.core import checks, exceptions
from django.db.models import Field, Func, IntegerField, Transform, Value
from django.db.models.fields.mixins import CheckFieldDefaultMixin
from django.db.models.lookups import Exact, FieldGetDbPrepValueMixin, In, Lookup
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _

from django_mongodb_backend.forms import SimpleArrayField
from django_mongodb_backend.query_utils import is_constant_value, process_lhs, process_rhs
from django_mongodb_backend.utils import prefix_validation_error
from django_mongodb_backend.validators import ArrayMaxLengthValidator, LengthValidator

__all__ = ["ArrayField"]


class AttributeSetter:
    def __init__(self, name, value):
        setattr(self, name, value)


class ArrayField(CheckFieldDefaultMixin, Field):
    empty_strings_allowed = False
    default_error_messages = {
        "item_invalid": _("Item %(nth)s in the array did not validate:"),
        "nested_array_mismatch": _("Nested arrays must have the same length."),
    }
    _default_hint = ("list", "[]")

    def __init__(self, base_field, max_size=None, size=None, **kwargs):
        self.base_field = base_field
        self.max_size = max_size
        self.size = size
        if self.max_size:
            self.default_validators = [
                *self.default_validators,
                ArrayMaxLengthValidator(self.max_size),
            ]
        if self.size:
            self.default_validators = [
                *self.default_validators,
                LengthValidator(self.size),
            ]
        # For performance, only add a from_db_value() method if the base field
        # implements it.
        if hasattr(self.base_field, "from_db_value"):
            self.from_db_value = self._from_db_value
        super().__init__(**kwargs)

    @property
    def model(self):
        try:
            return self.__dict__["model"]
        except KeyError:
            raise AttributeError(
                f"'{self.__class__.__name__}' object has no attribute 'model'"
            ) from None

    @model.setter
    def model(self, model):
        self.__dict__["model"] = model
        self.base_field.model = model

    @classmethod
    def _choices_is_value(cls, value):
        return isinstance(value, (list, tuple)) or super()._choices_is_value(value)

    def check(self, **kwargs):
        errors = super().check(**kwargs)
        if self.base_field.remote_field:
            errors.append(
                checks.Error(
                    "Base field for array cannot be a related field.",
                    obj=self,
                    id="django_mongodb_backend.array.E002",
                )
            )
        else:
            base_checks = self.base_field.check()
            if base_checks:
                error_messages = "\n    ".join(
                    f"{base_check.msg} ({base_check.id})"
                    for base_check in base_checks
                    if isinstance(base_check, checks.Error)
                )
                if error_messages:
                    errors.append(
                        checks.Error(
                            f"Base field for array has errors:\n    {error_messages}",
                            obj=self,
                            id="django_mongodb_backend.array.E001",
                        )
                    )
                warning_messages = "\n    ".join(
                    f"{base_check.msg} ({base_check.id})"
                    for base_check in base_checks
                    if isinstance(base_check, checks.Warning)
                )
                if warning_messages:
                    errors.append(
                        checks.Warning(
                            f"Base field for array has warnings:\n    {warning_messages}",
                            obj=self,
                            id="django_mongodb_backend.array.W004",
                        )
                    )
        if self.size and self.max_size:
            errors.append(
                checks.Error(
                    "ArrayField cannot have both size and max_size.",
                    obj=self,
                    id="django_mongodb_backend.array.E003",
                )
            )
        return errors

    def set_attributes_from_name(self, name):
        super().set_attributes_from_name(name)
        self.base_field.set_attributes_from_name(name)

    @property
    def description(self):
        return f"Array of {self.base_field.description}"

    def db_type(self, connection):
        return "array"

    def get_db_prep_value(self, value, connection, prepared=False):
        if isinstance(value, (list, tuple)):
            return [self.base_field.get_db_prep_value(i, connection, prepared=False) for i in value]
        return value

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        if path == "django_mongodb_backend.fields.array.ArrayField":
            path = "django_mongodb_backend.fields.ArrayField"
        kwargs["base_field"] = self.base_field.clone()
        if self.max_size is not None:
            kwargs["max_size"] = self.max_size
        if self.size is not None:
            kwargs["size"] = self.size
        return name, path, args, kwargs

    def to_python(self, value):
        if isinstance(value, str):
            # Assume value is being deserialized.
            vals = json.loads(value)
            value = [self.base_field.to_python(val) for val in vals]
        return value

    def _from_db_value(self, value, expression, connection):
        if value is None:
            return value
        return [self.base_field.from_db_value(item, expression, connection) for item in value]

    def value_to_string(self, obj):
        values = []
        vals = self.value_from_object(obj)
        base_field = self.base_field

        for val in vals:
            if val is None:
                values.append(None)
            else:
                obj = AttributeSetter(base_field.attname, val)
                values.append(base_field.value_to_string(obj))
        return json.dumps(values)

    def get_transform(self, name):
        transform = super().get_transform(name)
        if transform:
            return transform
        if "_" not in name:
            try:
                index = int(name)
            except ValueError:
                pass
            else:
                return IndexTransformFactory(index, self.base_field)
        try:
            start, end = name.split("_")
            start = int(start)
            end = int(end)
        except ValueError:
            pass
        else:
            return SliceTransformFactory(start, end)

    def validate(self, value, model_instance):
        super().validate(value, model_instance)
        for index, part in enumerate(value):
            try:
                self.base_field.validate(part, model_instance)
            except exceptions.ValidationError as error:
                raise prefix_validation_error(
                    error,
                    prefix=self.error_messages["item_invalid"],
                    code="item_invalid",
                    params={"nth": index + 1},
                ) from None
        if isinstance(self.base_field, ArrayField) and len({len(i) for i in value}) > 1:
            raise exceptions.ValidationError(
                self.error_messages["nested_array_mismatch"],
                code="nested_array_mismatch",
            )

    def run_validators(self, value):
        super().run_validators(value)
        for index, part in enumerate(value):
            try:
                self.base_field.run_validators(part)
            except exceptions.ValidationError as error:
                raise prefix_validation_error(
                    error,
                    prefix=self.error_messages["item_invalid"],
                    code="item_invalid",
                    params={"nth": index + 1},
                ) from None

    def formfield(self, **kwargs):
        return super().formfield(
            **{
                "form_class": SimpleArrayField,
                "base_field": self.base_field.formfield(),
                "max_length": self.max_size,
                "length": self.size,
                **kwargs,
            }
        )


class Array(Func):
    def as_mql_expr(self, compiler, connection):
        return [
            expr.as_mql(compiler, connection, as_expr=True)
            for expr in self.get_source_expressions()
        ]

    def as_mql_path(self, compiler, connection):
        return [expr.as_mql(compiler, connection) for expr in self.get_source_expressions()]

    @cached_property
    def can_use_path(self):
        return all(is_constant_value(expr) for expr in self.get_source_expressions())

    @property
    def is_simple_column(self):
        return False


class ArrayRHSMixin:
    def __init__(self, lhs, rhs):
        if isinstance(rhs, (tuple, list)):
            expressions = []
            for value in rhs:
                if not hasattr(value, "resolve_expression"):
                    field = lhs.output_field
                    value = Value(field.base_field.get_prep_value(value))
                expressions.append(value)
            rhs = Array(*expressions)
        super().__init__(lhs, rhs)


@ArrayField.register_lookup
class ArrayContains(ArrayRHSMixin, FieldGetDbPrepValueMixin, Lookup):
    lookup_name = "contains"

    def as_mql_expr(self, compiler, connection):
        lhs_mql = process_lhs(self, compiler, connection, as_expr=True)
        value = process_rhs(self, compiler, connection, as_expr=True)
        return {
            "$and": [
                {"$ne": [lhs_mql, None]},
                {"$ne": [value, None]},
                {"$setIsSubset": [value, lhs_mql]},
            ]
        }

    def as_mql_path(self, compiler, connection):
        lhs_mql = process_lhs(self, compiler, connection)
        value = process_rhs(self, compiler, connection)
        return {lhs_mql: {"$all": value}}


@ArrayField.register_lookup
class ArrayContainedBy(ArrayRHSMixin, FieldGetDbPrepValueMixin, Lookup):
    lookup_name = "contained_by"

    def as_mql_expr(self, compiler, connection):
        lhs_mql = process_lhs(self, compiler, connection, as_expr=True)
        value = process_rhs(self, compiler, connection, as_expr=True)
        return {
            "$and": [
                {"$ne": [lhs_mql, None]},
                {"$ne": [value, None]},
                {"$setIsSubset": [lhs_mql, value]},
            ]
        }


@ArrayField.register_lookup
class ArrayExact(ArrayRHSMixin, Exact):
    pass


@ArrayField.register_lookup
class ArrayOverlap(ArrayRHSMixin, FieldGetDbPrepValueMixin, Lookup):
    lookup_name = "overlap"

    def get_subquery_wrapping_pipeline(self, compiler, connection, field_name, expr):
        return [
            {"$project": {"subquery_results": expr.as_mql(compiler, connection, as_expr=True)}},
            {"$unwind": "$subquery_results"},
            {
                "$group": {
                    "_id": None,
                    "subquery_results": {"$addToSet": "$subquery_results"},
                }
            },
            # Workaround for https://jira.mongodb.org/browse/SERVER-114196:
            # $$NOW becomes unavailable after $unionWith, so it must be stored
            # beforehand to ensure it remains accessible later in the pipeline.
            {"$addFields": {"__now": "$$NOW"}},
            # Add an extra empty document to handle default values on empty
            # results.
            {"$unionWith": {"pipeline": [{"$documents": [{"subquery_results": []}]}]}},
            {"$limit": 1},
            {"$project": {field_name: "$subquery_results"}},
        ]

    def as_mql_expr(self, compiler, connection):
        lhs_mql = process_lhs(self, compiler, connection, as_expr=True)
        value = process_rhs(self, compiler, connection, as_expr=True)
        return {
            "$and": [
                {"$ne": [lhs_mql, None]},
                {"$size": {"$setIntersection": [value, lhs_mql]}},
            ]
        }

    def as_mql_path(self, compiler, connection):
        lhs_mql = process_lhs(self, compiler, connection)
        value = process_rhs(self, compiler, connection)
        return {lhs_mql: {"$in": value}}


@ArrayField.register_lookup
class ArrayLenTransform(Transform):
    lookup_name = "len"
    output_field = IntegerField()

    def as_mql_expr(self, compiler, connection):
        lhs_mql = process_lhs(self, compiler, connection, as_expr=True)
        return {"$cond": {"if": {"$isArray": lhs_mql}, "then": {"$size": lhs_mql}, "else": None}}


@ArrayField.register_lookup
class ArrayInLookup(In):
    def get_prep_lookup(self):
        values = super().get_prep_lookup()
        if hasattr(values, "resolve_expression"):
            return values
        # process_rhs() expects hashable values, so convert lists to tuples.
        prepared_values = []
        for value in values:
            if hasattr(value, "resolve_expression"):
                prepared_values.append(value)
            else:
                prepared_values.append(tuple(value))
        return prepared_values


class IndexTransform(Transform):
    def __init__(self, index, base_field, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.index = index
        self.base_field = base_field

    def as_mql_expr(self, compiler, connection):
        lhs_mql = process_lhs(self, compiler, connection, as_expr=True)
        return {"$arrayElemAt": [lhs_mql, self.index]}

    def as_mql_path(self, compiler, connection):
        lhs_mql = process_lhs(self, compiler, connection)
        return f"{lhs_mql}.{self.index}"

    @property
    def output_field(self):
        return self.base_field

    @property
    def can_use_path(self):
        return self.is_simple_column

    @property
    def is_simple_column(self):
        return self.lhs.is_simple_column


class IndexTransformFactory:
    def __init__(self, index, base_field):
        self.index = index
        self.base_field = base_field

    def __call__(self, *args, **kwargs):
        return IndexTransform(self.index, self.base_field, *args, **kwargs)


class SliceTransform(Transform):
    def __init__(self, start, end, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start = start
        self.end = end

    def as_mql_expr(self, compiler, connection):
        lhs_mql = process_lhs(self, compiler, connection, as_expr=True)
        return {"$slice": [lhs_mql, self.start, self.end]}


class SliceTransformFactory:
    def __init__(self, start, end):
        self.start = start
        self.end = end

    def __call__(self, *args, **kwargs):
        return SliceTransform(self.start, self.end, *args, **kwargs)
