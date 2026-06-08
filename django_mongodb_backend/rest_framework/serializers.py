from __future__ import annotations

from typing import Any

from django.core.exceptions import FieldDoesNotExist
from django.db import models
from rest_framework import serializers
from rest_framework.fields import CharField, ChoiceField, Field
from rest_framework.serializers import ModelField
from rest_framework.utils.field_mapping import ClassLookupDict, get_field_kwargs
from rest_framework.validators import UniqueValidator

from django_mongodb_backend.fields import (
    ArrayField,
    EmbeddedModelArrayField,
    EmbeddedModelField,
    ObjectIdAutoField,
    ObjectIdField,
    PolymorphicEmbeddedModelArrayField,
    PolymorphicEmbeddedModelField,
)

# Built once at import time; callers may pass a custom mapping to override.
_FIELD_MAPPING: ClassLookupDict = ClassLookupDict(
    {
        **serializers.ModelSerializer.serializer_field_mapping,
        ObjectIdAutoField: serializers.CharField,
        ObjectIdField: serializers.CharField,
    }
)


def _make_embedded_serializer(embedded_model: type[Any]) -> type[EmbeddedModelSerializer]:
    return type(
        f"{embedded_model.__name__}Serializer",
        (EmbeddedModelSerializer,),
        {"Meta": type("Meta", (), {"model": embedded_model, "fields": "__all__"})},
    )


def _build_embedded_field(
    model_field: models.Field[Any, Any],
    field_mapping: ClassLookupDict | None = None,
) -> tuple[type[Any], dict[str, Any]] | None:
    """Return (field_class, kwargs) for MongoDB-specific fields, or None for standard fields."""
    if isinstance(model_field, (PolymorphicEmbeddedModelField, PolymorphicEmbeddedModelArrayField)):
        raise NotImplementedError(
            f"Field '{model_field.name}' uses a polymorphic embedded field type which is not "
            "supported automatically. Declare the field manually on the serializer."
        )

    # EmbeddedModelArrayField before ArrayField — subclass check must come first.
    if isinstance(model_field, EmbeddedModelArrayField):
        child_cls = _make_embedded_serializer(model_field.embedded_model)
        kwargs: dict[str, Any] = {"many": True}
        if model_field.null:
            kwargs["allow_null"] = True
        return child_cls, kwargs

    if isinstance(model_field, EmbeddedModelField):
        field_cls = _make_embedded_serializer(model_field.embedded_model)
        kwargs = {}
        if model_field.null:
            kwargs["allow_null"] = True
        return field_cls, kwargs

    if isinstance(model_field, ArrayField):
        child_field = _get_serializer_field(model_field.base_field, field_mapping)
        kwargs = {}
        if model_field.null:
            kwargs["allow_null"] = True
        if child_field is not None:
            kwargs["child"] = child_field
        return serializers.ListField, kwargs

    return None


def _get_serializer_field(
    model_field: models.Field[Any, Any],
    field_mapping: ClassLookupDict | None = None,
) -> Field[Any, Any, Any, Any] | None:
    """Return a DRF field instance for model_field, or None to skip it."""
    if model_field.primary_key:
        return None

    result = _build_embedded_field(model_field, field_mapping)
    if result is not None:
        field_cls, kwargs = result
        return field_cls(**kwargs)

    mapping = field_mapping if field_mapping is not None else _FIELD_MAPPING
    try:
        field_class: type[Field[Any, Any, Any, Any]] = mapping[model_field]
    except KeyError:
        return None
    field_kwargs: dict[str, Any] = get_field_kwargs(model_field.name, model_field)
    # model_field is only valid for DRF's ModelField fallback; strip it for all others.
    if not issubclass(field_class, ModelField):
        field_kwargs.pop("model_field", None)
    # allow_blank is only valid for CharField and ChoiceField.
    if not issubclass(field_class, (CharField, ChoiceField)):
        field_kwargs.pop("allow_blank", None)
    # EmbeddedModels cannot be queried; UniqueValidator would crash at is_valid() time.
    if "validators" in field_kwargs:
        field_kwargs["validators"] = [
            v for v in field_kwargs["validators"] if not isinstance(v, UniqueValidator)
        ]
    return field_class(**field_kwargs)


class EmbeddedModelSerializer(serializers.Serializer):
    """
    Serializer for EmbeddedModel instances.

    Subclass and set ``Meta.model`` and ``Meta.fields``::

        class AddressSerializer(EmbeddedModelSerializer):
            class Meta:
                model = Address
                fields = '__all__'

    ``EmbeddedModelSerializer`` auto-generates DRF fields from the embedded
    model's field definitions, including nested ``EmbeddedModelField`` and
    ``EmbeddedModelArrayField``. ``PolymorphicEmbeddedModelField`` fields must
    be declared explicitly.
    """

    class Meta:
        model: type[Any]
        fields: list[str] | str

    def get_fields(self) -> dict[str, Field[Any, Any, Any, Any]]:
        assert hasattr(self, "Meta"), f"Class {self.__class__.__name__} missing 'Meta' attribute."
        meta = type(self).Meta
        assert hasattr(meta, "model"), (
            f"Class {self.__class__.__name__}.Meta missing 'model' attribute."
        )
        assert hasattr(meta, "fields"), (
            f"Class {self.__class__.__name__}.Meta missing 'fields' attribute."
        )

        embedded_model: type[Any] = meta.model
        all_fields = {f.name: f for f in embedded_model._meta.fields}

        explicit = meta.fields != "__all__"
        field_names: list[str] | str = meta.fields
        if field_names == "__all__":
            field_names = list(all_fields)
        elif not isinstance(field_names, (list, tuple)):
            raise AssertionError(
                f"{self.__class__.__name__}.Meta.fields must be '__all__' or a list/tuple."
            )

        result: dict[str, Field[Any, Any, Any, Any]] = {}
        for name in field_names:
            model_field = all_fields.get(name)
            if model_field is None:
                raise FieldDoesNotExist(f"Field '{name}' not found on {embedded_model.__name__}.")
            if explicit and model_field.primary_key:
                raise ValueError(
                    f"Primary key field '{name}' cannot be included in "
                    f"{self.__class__.__name__}.Meta.fields. "
                    "EmbeddedModelSerializer excludes primary keys automatically."
                )
            drf_field = _get_serializer_field(model_field)
            if drf_field is not None:
                result[name] = drf_field
        return result

    def to_internal_value(self, data: Any) -> Any:
        validated: dict[str, Any] = super().to_internal_value(data)
        meta = type(self).Meta
        return meta.model(**validated)

    def create(self, validated_data: Any) -> Any:
        raise NotImplementedError("EmbeddedModel instances cannot be saved independently.")

    def update(self, instance: Any, validated_data: Any) -> Any:
        raise NotImplementedError("EmbeddedModel instances cannot be updated independently.")


class MongoModelSerializer(serializers.ModelSerializer):
    """
    ``ModelSerializer`` with automatic support for MongoDB-specific fields.

    ``EmbeddedModelField``, ``EmbeddedModelArrayField``, and ``ArrayField``
    are detected automatically. ``PolymorphicEmbeddedModelField`` fields must
    be declared explicitly::

        class BookSerializer(MongoModelSerializer):
            class Meta:
                model = Book
                fields = '__all__'

    Explicit field declarations override the auto-generated fields::

        class BookSerializer(MongoModelSerializer):
            author = AuthorSerializer()

            class Meta:
                model = Book
                fields = '__all__'
    """

    serializer_field_mapping = {
        **serializers.ModelSerializer.serializer_field_mapping,
        ObjectIdAutoField: serializers.CharField,
        ObjectIdField: serializers.CharField,
    }

    def build_field(
        self,
        field_name: str,
        info: Any,
        model_class: type[models.Model],
        nested_depth: int,
    ) -> tuple[type[Any], dict[str, Any]]:
        try:
            model_field = model_class._meta.get_field(field_name)
        except FieldDoesNotExist:
            return super().build_field(field_name, info, model_class, nested_depth)

        if not isinstance(model_field, models.Field):
            return super().build_field(field_name, info, model_class, nested_depth)

        result = _build_embedded_field(model_field, ClassLookupDict(self.serializer_field_mapping))
        if result is not None:
            return result

        return super().build_field(field_name, info, model_class, nested_depth)
