import difflib

from django.core.exceptions import FieldDoesNotExist
from django.db.models import Field, lookups
from django.db.models.expressions import Col
from django.db.models.fields.related import lazy_related_operation
from django.db.models.lookups import Lookup, Transform

from .. import forms
from ..query_utils import process_lhs, process_rhs
from . import EmbeddedModelField
from .array import ArrayField, ArrayLenTransform


class EmbeddedModelArrayField(ArrayField):
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
        if isinstance(value, list | tuple):
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
        return KeyTransformFactory(name, self)

    def _get_lookup(self, lookup_name):
        lookup = super()._get_lookup(lookup_name)
        if lookup is None or lookup is ArrayLenTransform:
            return lookup

        class EmbeddedModelArrayFieldLookups(Lookup):
            def as_mql(self, compiler, connection):
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
    def process_rhs(self, compiler, connection):
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

    def as_mql(self, compiler, connection):
        # Querying a subfield within the array elements (via nested
        # KeyTransform). Replicate MongoDB's implicit ANY-match by mapping over
        # the array and applying $in on the subfield.
        lhs_mql = process_lhs(self, compiler, connection)
        inner_lhs_mql = lhs_mql["$ifNull"][0]["$map"]["in"]
        values = process_rhs(self, compiler, connection)
        lhs_mql["$ifNull"][0]["$map"]["in"] = connection.mongo_operators[self.lookup_name](
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
            {
                "$facet": {
                    "gathered_data": [
                        {"$project": {"tmp_name": expr.as_mql(compiler, connection)}},
                        # To concatenate all the values from the RHS subquery,
                        # use an $unwind followed by a $group.
                        {
                            "$unwind": "$tmp_name",
                        },
                        # The $group stage collects values into an array using
                        # $addToSet. The use of {_id: null} results in a
                        # single grouped array. However, because arrays from
                        # multiple documents are aggregated, the result is a
                        # list of lists.
                        {
                            "$group": {
                                "_id": None,
                                "tmp_name": {"$addToSet": "$tmp_name"},
                            }
                        },
                    ]
                }
            },
            {
                "$project": {
                    field_name: {
                        "$ifNull": [
                            {
                                "$getField": {
                                    "input": {"$arrayElemAt": ["$gathered_data", 0]},
                                    "field": "tmp_name",
                                }
                            },
                            [],
                        ]
                    }
                }
            },
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


class KeyTransform(Transform):
    field_class_name = "EmbeddedModelArrayField"

    def __init__(self, key_name, array_field, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.array_field = array_field
        self.key_name = key_name
        # Lookups iterate over the array of embedded models. A virtual column
        # of the queried field's type represents each element.
        column_target = array_field.base_field.embedded_model._meta.get_field(key_name).clone()
        column_name = f"$item.{key_name}"
        column_target.db_column = column_name
        column_target.set_attributes_from_name(column_name)
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
            if isinstance(transform, KeyTransformFactory):
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

    def as_mql(self, compiler, connection):
        inner_lhs_mql = self._lhs.as_mql(compiler, connection)
        lhs_mql = process_lhs(self, compiler, connection)
        return {
            "$ifNull": [
                {
                    "$map": {
                        "input": lhs_mql,
                        "as": "item",
                        "in": inner_lhs_mql,
                    }
                },
                [],
            ]
        }

    @property
    def output_field(self):
        return _EmbeddedModelArrayOutputField(self._lhs.output_field)


class KeyTransformFactory:
    def __init__(self, key_name, base_field):
        self.key_name = key_name
        self.base_field = base_field

    def __call__(self, *args, **kwargs):
        return KeyTransform(self.key_name, self.base_field, *args, **kwargs)
