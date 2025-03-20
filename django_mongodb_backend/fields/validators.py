from django.core.validators import BaseValidator
from django.utils.deconstruct import deconstructible
from django.utils.translation import ngettext_lazy


@deconstructible
class LengthValidator(BaseValidator):
    message = ngettext_lazy(
        "List contains %(show_value)d item, it should contain %(limit_value)d.",
        "List contains %(show_value)d items, it should contain %(limit_value)d.",
        "show_value",
    )
    code = "length"

    def compare(self, a, b):
        return a != b

    def clean(self, x):
        return len(x)
