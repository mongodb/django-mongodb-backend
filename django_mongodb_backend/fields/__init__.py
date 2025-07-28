from .array import ArrayField
from .auto import ObjectIdAutoField
from .duration import register_duration_field
from .embedded_model import EmbeddedModelField
from .embedded_model_array import EmbeddedModelArrayField
from .json import register_json_field
from .objectid import ObjectIdField
from .polymorphic_embedded_model import PolymorphicEmbeddedModelField
from .polymorphic_embedded_model_array import PolymorphicEmbeddedModelArrayField

__all__ = [
    "ArrayField",
    "EmbeddedModelArrayField",
    "EmbeddedModelField",
    "ObjectIdAutoField",
    "ObjectIdField",
    "PolymorphicEmbeddedModelArrayField",
    "PolymorphicEmbeddedModelField",
    "register_fields",
]


def register_fields():
    register_duration_field()
    register_json_field()
