import difflib

from django.core.exceptions import FieldDoesNotExist
from django.db.models import Field, lookups
from django.db.models.expressions import Col
from django.db.models.fields.related import lazy_related_operation
from django.db.models.lookups import Lookup, Transform
from django.utils.functional import cached_property

from django_mongodb_backend import forms
from django_mongodb_backend.fields import EmbeddedModelField
from django_mongodb_backend.fields.array import ArrayField, ArrayLenTransform
from django_mongodb_backend.query_utils import process_lhs, process_rhs

from .mixins import NoEncryptedEmbeddedFieldsMixin


class EmbeddedModelArrayField(NoEncryptedEmbeddedFieldsMixin, ArrayField):
    def __init__(self, embedded_model, **kwargs):
        if "size" in kwargs:
            raise ValueError("EmbeddedModelArrayField does not support size.")
        super().__init__(EmbeddedModelField(embedded_model), **kwargs)
        self.embedded_model = embedded_model

    def contribute_to_class(self, cls, name, private_only=False, **kwargs):
        super().contribute_to_class(cls, name, private_only=private_only, **kwargs)

        if not cls._meta.abstract:
            # If embedded_models contains any strings, replace them with the actual
            # model classes.
            def _resolve_lookup(_, resolved_model):
                self.embedded_model = resolved_model

            lazy_related_operation(_resolve_lookup, cls, self.embedded_model)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        if path == "django_mongodb_backend.fields.embedded_model_array.EmbeddedModelArrayField":
            path = "django_mongodb_backend.fields.EmbeddedModelArrayField"
        kwargs["embedded_model"] = self.embedded_model
        del kwargs["base_field"]
        return name, path, args, kwargs

    def get_db_prep_value(self, value, connection, prepared=False):
        if isinstance(value, (list, tuple)):
            # Must call get_db_prep_save() rather than get_db_prep_value()
            # to transform model instances to dicts.
            return [self.base_field.get_db_prep_save(i, connection) for i in value]
        if value is not None:
            raise TypeError(
                f"Expected list of {self.embedded_model!r} instances, not {type(value)!r}."
            )
        return value

    def formfield(self, **kwargs):
        # Skip ArrayField.formfield() which has some differences, including
        # unneeded "base_field", and "max_length" instead of "max_num".
        return Field.formfield(
            self,
            **{
                "form_class": forms.EmbeddedModelArrayField,
                "model": self.embedded_model,
                "max_num": self.max_size,
                "prefix": self.name,
                **kwargs,
            },
        )

    def get_transform(self, name):
        transform = super().get_transform(name)
        if transform:
            return transform
        field = self.base_field.embedded_model._meta.get_field(name)
        return EmbeddedModelArrayFieldTransformFactory(field)

    def _get_lookup(self, lookup_name):
        lookup = super()._get_lookup(lookup_name)
        if lookup is None or lookup is ArrayLenTransform:
            return lookup

        class EmbeddedModelArrayFieldLookups(Lookup):
            def as_mql(self, compiler, connection, as_expr=False):
                raise ValueError(
                    "Lookups aren't supported on EmbeddedModelArrayField. "
                    "Try querying one of its embedded fields instead."
                )

        return EmbeddedModelArrayFieldLookups


class _EmbeddedModelArrayOutputField(ArrayField):
    """
    Represent the output of an EmbeddedModelArrayField when traversed in a
    query path.

    This field is not meant to be used in model definitions. It exists solely
    to support query output resolution. When an EmbeddedModelArrayField is
    accessed in a query, the result should behave like an array of the embedded
    model's target type.

    While it mimics ArrayField's lookup behavior, the way those lookups are
    resolved follows the semantics of EmbeddedModelArrayField rather than
    ArrayField.
    """

    ALLOWED_LOOKUPS = {
        "in",
        "exact",
        "iexact",
        "gt",
        "gte",
        "lt",
        "lte",
    }

    def get_lookup(self, name):
        return super().get_lookup(name) if name in self.ALLOWED_LOOKUPS else None


class EmbeddedModelArrayFieldBuiltinLookup(Lookup):
    def process_rhs(self, compiler, connection, as_expr=False):
        value = self.rhs
        if not self.get_db_prep_lookup_value_is_iterable:
            value = [value]
        # Value must be serialized based on the query target. If querying a
        # subfield inside the array (i.e., a nested KeyTransform), use the
        # output field of the subfield. Otherwise, use the base field of the
        # array itself.
        get_db_prep_value = self.lhs._lhs.output_field.get_db_prep_value
        return None, [
            v if hasattr(v, "as_mql") else get_db_prep_value(v, connection, prepared=True)
            for v in value
        ]

    def as_mql_expr(self, compiler, connection):
        # Querying a subfield within the array elements (via nested
        # KeyTransform). Replicate MongoDB's implicit ANY-match by mapping over
        # the array and applying $in on the subfield.
        lhs_mql = process_lhs(self, compiler, connection, as_expr=True)
        inner_lhs_mql = lhs_mql["$ifNull"][0]["$map"]["in"]
        values = process_rhs(self, compiler, connection, as_expr=True)
        lhs_mql["$ifNull"][0]["$map"]["in"] = connection.mongo_expr_operators[self.lookup_name](
            inner_lhs_mql, values
        )
        return {"$anyElementTrue": lhs_mql}


@_EmbeddedModelArrayOutputField.register_lookup
class EmbeddedModelArrayFieldIn(EmbeddedModelArrayFieldBuiltinLookup, lookups.In):
    def get_subquery_wrapping_pipeline(self, compiler, connection, field_name, expr):
        # This pipeline is adapted from that of ArrayField, because the
        # structure of EmbeddedModelArrayField on the RHS behaves similar to
        # ArrayField.
        return [
            {"$project": {"subquery_results": expr.as_mql(compiler, connection, as_expr=True)}},
            # Use an $unwind followed by a $group to concatenate all the values
            # from the RHS subquery.
            {"$unwind": "$subquery_results"},
            # The $group stage collects values into an array using $addToSet.
            # The use of {_id: null} results in a single grouped array, but
            # because arrays from multiple documents are aggregated, the result
            # is a list of lists.
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
            # Add a dummy document in case of an empty result.
            {"$unionWith": {"pipeline": [{"$documents": [{"subquery_results": []}]}]}},
            {"$limit": 1},
            {"$project": {field_name: "$subquery_results"}},
        ]


@_EmbeddedModelArrayOutputField.register_lookup
class EmbeddedModelArrayFieldExact(EmbeddedModelArrayFieldBuiltinLookup, lookups.Exact):
    pass


@_EmbeddedModelArrayOutputField.register_lookup
class EmbeddedModelArrayFieldIExact(EmbeddedModelArrayFieldBuiltinLookup, lookups.IExact):
    get_db_prep_lookup_value_is_iterable = False


@_EmbeddedModelArrayOutputField.register_lookup
class EmbeddedModelArrayFieldGreaterThan(EmbeddedModelArrayFieldBuiltinLookup, lookups.GreaterThan):
    pass


@_EmbeddedModelArrayOutputField.register_lookup
class EmbeddedModelArrayFieldGreaterThanOrEqual(
    EmbeddedModelArrayFieldBuiltinLookup, lookups.GreaterThanOrEqual
):
    pass


@_EmbeddedModelArrayOutputField.register_lookup
class EmbeddedModelArrayFieldLessThan(EmbeddedModelArrayFieldBuiltinLookup, lookups.LessThan):
    pass


@_EmbeddedModelArrayOutputField.register_lookup
class EmbeddedModelArrayFieldLessThanOrEqual(
    EmbeddedModelArrayFieldBuiltinLookup, lookups.LessThanOrEqual
):
    pass


class EmbeddedModelArrayFieldTransform(Transform):
    field_class_name = "EmbeddedModelArrayField"
    VIRTUAL_COLUMN_ITERABLE = "item"

    def __init__(self, field, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Lookups iterate over the array of embedded models. A virtual column
        # of the queried field's type represents each element.
        column_target = field.clone()
        column_name = f"${self.VIRTUAL_COLUMN_ITERABLE}.{field.column}"
        column_target.db_column = column_name
        column_target.set_attributes_from_name(column_name)
        self._field = field
        self._lhs = Col(None, column_target)
        self._sub_transform = None

    def __call__(self, this, *args, **kwargs):
        self._lhs = self._sub_transform(self._lhs, *args, **kwargs)
        return self

    def get_lookup(self, name):
        return self.output_field.get_lookup(name)

    def get_transform(self, name):
        """
        Validate that `name` is either a field of an embedded model or am
        allowed lookup on an embedded model's field.
        """
        # Once the sub-lhs is a transform, all the filters are applied over it.
        # Otherwise get the transform from the nested embedded model field.
        if transform := self._lhs.get_transform(name):
            if isinstance(transform, EmbeddedModelArrayFieldTransformFactory):
                raise ValueError("Cannot perform multiple levels of array traversal in a query.")
            self._sub_transform = transform
            return self
        output_field = self._lhs.output_field
        # The lookup must be allowed AND a valid lookup for the field.
        allowed_lookups = self.output_field.ALLOWED_LOOKUPS.intersection(
            set(output_field.get_lookups())
        )
        suggested_lookups = difflib.get_close_matches(name, allowed_lookups)
        if suggested_lookups:
            suggested_lookups = " or ".join(suggested_lookups)
            suggestion = f", perhaps you meant {suggested_lookups}?"
        else:
            suggestion = ""
        raise FieldDoesNotExist(
            f"Unsupported lookup '{name}' for "
            f"{self.field_class_name} of '{output_field.__class__.__name__}'"
            f"{suggestion}"
        )

    def as_mql_expr(self, compiler, connection):
        inner_lhs_mql = self._lhs.as_mql(compiler, connection, as_expr=True)
        lhs_mql = process_lhs(self, compiler, connection, as_expr=True)
        return {
            "$ifNull": [
                {
                    "$map": {
                        "input": lhs_mql,
                        "as": self.VIRTUAL_COLUMN_ITERABLE,
                        "in": inner_lhs_mql,
                    }
                },
                [],
            ]
        }

    def as_mql_path(self, compiler, connection):
        inner_lhs_mql = self._lhs.as_mql(compiler, connection).removeprefix(
            f"${self.VIRTUAL_COLUMN_ITERABLE}."
        )
        lhs_mql = process_lhs(self, compiler, connection)
        return f"{lhs_mql}.{inner_lhs_mql}"

    @property
    def output_field(self):
        return _EmbeddedModelArrayOutputField(self._lhs.output_field)

    @property
    def can_use_path(self):
        return self.is_simple_column

    @cached_property
    def is_simple_column(self):
        previous = self
        while isinstance(previous, EmbeddedModelArrayFieldTransform):
            previous = previous.lhs
        return previous.is_simple_column and self._lhs.is_simple_column


class EmbeddedModelArrayFieldTransformFactory:
    def __init__(self, field):
        self.field = field

    def __call__(self, *args, **kwargs):
        return EmbeddedModelArrayFieldTransform(self.field, *args, **kwargs)
