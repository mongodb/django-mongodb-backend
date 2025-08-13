from .array import ArrayField
from .auto import ObjectIdAutoField
from .duration import register_duration_field
from .embedded_model import EmbeddedModelField
from .embedded_model_array import EmbeddedModelArrayField
from .encryption import (
    EncryptedBinaryField,
    EncryptedBooleanField,
    EncryptedCharField,
    EncryptedDateField,
    EncryptedDateTimeField,
    EncryptedDecimalField,
    EncryptedDurationField,
    EncryptedEmailField,
    EncryptedFieldMixin,
    EncryptedFloatField,
    EncryptedGenericIPAddressField,
    EncryptedIntegerField,
    EncryptedPositiveIntegerField,
    EncryptedPositiveSmallIntegerField,
    EncryptedSmallIntegerField,
    EncryptedTextField,
    EncryptedTimeField,
    EncryptedURLField,
)
from .json import register_json_field
from .objectid import ObjectIdField
from .polymorphic_embedded_model import PolymorphicEmbeddedModelField
from .polymorphic_embedded_model_array import PolymorphicEmbeddedModelArrayField

__all__ = [
    "ArrayField",
    "EmbeddedModelArrayField",
    "EmbeddedModelField",
    "EncryptedBinaryField",
    "EncryptedBooleanField",
    "EncryptedCharField",
    "EncryptedDateField",
    "EncryptedDateTimeField",
    "EncryptedDecimalField",
    "EncryptedDurationField",
    "EncryptedEmailField",
    "EncryptedFieldMixin",
    "EncryptedFloatField",
    "EncryptedGenericIPAddressField",
    "EncryptedIntegerField",
    "EncryptedPositiveIntegerField",
    "EncryptedPositiveSmallIntegerField",
    "EncryptedSmallIntegerField",
    "EncryptedTextField",
    "EncryptedTimeField",
    "EncryptedURLField",
    "ObjectIdAutoField",
    "ObjectIdField",
    "PolymorphicEmbeddedModelArrayField",
    "PolymorphicEmbeddedModelField",
    "register_fields",
]


def register_fields():
    register_duration_field()
    register_json_field()
