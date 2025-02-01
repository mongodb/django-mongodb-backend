from django import forms
from django.core.exceptions import ValidationError
from django.forms import formset_factory, model_to_dict
from django.forms.models import modelform_factory
from django.utils.html import format_html, format_html_join


class EmbeddedModelArrayField(forms.Field):
    def __init__(self, model, *, prefix, max_num=None, extra_forms=3, **kwargs):
        self.model = model
        self.prefix = prefix
        self.formset = formset_factory(
            form=modelform_factory(model, fields="__all__"),
            can_delete=True,
            max_num=max_num,
            extra=extra_forms,
            validate_max=True,
        )
        kwargs["widget"] = EmbeddedModelArrayWidget()
        super().__init__(**kwargs)

    def clean(self, value):
        if not value:
            return []
        formset = self.formset(value, prefix=self.prefix_override or self.prefix)
        if not formset.is_valid():
            raise ValidationError(formset.errors + formset.non_form_errors())
        cleaned_data = []
        for data in formset.cleaned_data:
            # The "delete" checkbox isn't part of model data and must be
            # removed. The fallback to True skips empty forms.
            if data.pop("DELETE", True):
                continue
            cleaned_data.append(self.model(**data))
        return cleaned_data

    def has_changed(self, initial, data):
        formset = self.formset(data, initial=models_to_dicts(initial), prefix=self.prefix)
        return formset.has_changed()

    def get_bound_field(self, form, field_name):
        # Nested embedded model form fields need a double prefix.
        # HACK: Setting self.prefix_override makes it available in clean()
        # which doesn't have access to the form.
        self.prefix_override = f"{form.prefix}-{self.prefix}" if form.prefix else None
        return EmbeddedModelArrayBoundField(form, self, field_name, self.prefix_override)


class EmbeddedModelArrayBoundField(forms.BoundField):
    def __init__(self, form, field, name, prefix_override):
        super().__init__(form, field, name)
        self.formset = field.formset(
            self.data if form.is_bound else None,
            initial=models_to_dicts(self.initial),
            prefix=prefix_override if prefix_override else self.html_name,
        )

    def __str__(self):
        body = format_html_join(
            "\n", "<tbody>{}</tbody>", ((form.as_table(),) for form in self.formset)
        )
        return format_html("<table>\n{}\n</table>\n{}", body, self.formset.management_form)


class EmbeddedModelArrayWidget(forms.Widget):
    """
    Extract the data for EmbeddedModelArrayFormField's formset.
    This widget is never rendered.
    """

    def value_from_datadict(self, data, files, name):
        return {field: value for field, value in data.items() if field.startswith(f"{name}-")}


def models_to_dicts(models):
    """
    Convert initial data (which is a list of model instances or None) to a
    list of dictionary data suitable for a formset.
    """
    return [model_to_dict(model) for model in models or []]
