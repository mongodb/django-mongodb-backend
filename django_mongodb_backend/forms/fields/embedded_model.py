from django import forms
from django.forms.models import modelform_factory
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _


class EmbeddedModelField(forms.MultiValueField):
    default_error_messages = {
        "invalid": _("Enter a list of values."),
        "incomplete": _("Enter all required values."),
    }

    def __init__(self, model, prefix, *args, **kwargs):
        form_kwargs = {}
        # To avoid collisions with other fields on the form, each subfield must
        # be prefixed with the name of the field.
        form_kwargs["prefix"] = prefix
        self.form_kwargs = form_kwargs
        self.model_form_cls = modelform_factory(model, fields="__all__")
        self.model_form = self.model_form_cls(**form_kwargs)
        self.field_names = list(self.model_form.fields.keys())
        fields = self.model_form.fields.values()
        widgets = [field.widget for field in fields]
        widget = EmbeddedModelWidget(self.field_names, widgets)
        super().__init__(*args, fields=fields, widget=widget, require_all_fields=False, **kwargs)

    def compress(self, data_dict):
        if not data_dict:
            return None
        values = dict(zip(self.field_names, data_dict, strict=False))
        return self.model_form._meta.model(**values)

    def get_bound_field(self, form, field_name):
        # Nested embedded model form fields need a double prefix.
        prefix_override = f"{form.prefix}-{self.model_form.prefix}" if form.prefix else None
        return EmbeddedModelBoundField(form, self, field_name, prefix_override)

    def bound_data(self, data, initial):
        if self.disabled:
            return initial
        # Transform the bound data into a model instance.
        return self.compress(data)

    def prepare_value(self, value):
        # When rendering a form with errors, nested EmbeddedModelField data
        # won't be compressed if MultiValueField.clean() raises ValidationError
        # error before compress() is called. The data must be compressed here
        # so that EmbeddedModelBoundField.value() returns a model instance
        # (rather than a list) for initializing the form in
        # EmbeddedModelBoundField.__str__().
        return self.compress(value) if isinstance(value, list) else value


class EmbeddedModelBoundField(forms.BoundField):
    def __init__(self, form, field, name, prefix_override=None):
        super().__init__(form, field, name)
        # prefix_override overrides the prefix in self.field.form_kwargs so
        # that nested embedded model form elements have the correct name.
        self.prefix_override = prefix_override

    def __str__(self):
        """Render the model form as the representation for this field."""
        form = self.field.model_form_cls(instance=self.value(), **self.field.form_kwargs)
        if self.prefix_override:
            form.prefix = self.prefix_override
        return mark_safe(f"{form.as_div()}")  # noqa: S308


class EmbeddedModelWidget(forms.MultiWidget):
    def __init__(self, field_names, *args, **kwargs):
        self.field_names = field_names
        super().__init__(*args, **kwargs)
        # The default widget names are "_0", "_1", etc. Use the field names
        # instead since that's how they'll be rendered by the model form.
        self.widgets_names = ["-" + name for name in field_names]

    def decompress(self, value):
        if value is None:
            return []
        # Get the data from `value` (a model) for each field.
        return [getattr(value, name) for name in self.field_names]
