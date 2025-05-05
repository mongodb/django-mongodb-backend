from django import forms
from django.core.exceptions import ValidationError
from django.forms import formset_factory, model_to_dict
from django.forms.models import modelform_factory
from django.utils.html import format_html, format_html_join


def models_to_dicts(models):
    """
    Convert initial data (which is a list of model instances or None) to a
    list of dictionary data suitable for a formset.
    """
    return [model_to_dict(model) for model in models or []]


class EmbeddedModelArrayFormField(forms.Field):
    def __init__(self, model, prefix, max_length=None, *args, **kwargs):
        kwargs.pop("base_field")
        self.model = model
        self.prefix = prefix
        self.formset = formset_factory(
            form=modelform_factory(model, fields="__all__"),
            can_delete=True,
            max_num=max_length,
        )
        kwargs["widget"] = MultipleEmbeddedModelWidget()
        super().__init__(*args, **kwargs)

    def clean(self, value):
        if not value:
            # TODO: null or empty list?
            return []
        formset = self.formset(value, prefix=self.prefix)
        if not formset.is_valid():
            raise ValidationError(formset.errors)
        cleaned_data = []
        for data in formset.cleaned_data:
            # The fallback to True skips empty forms.
            if data.get("DELETE", True):
                continue
            data.pop("DELETE")  # The "delete" checkbox isn't part of model data.
            cleaned_data.append(self.model(**data))
        return cleaned_data

    def has_changed(self, initial, data):
        formset = self.formset(data, initial=models_to_dicts(initial), prefix=self.prefix)
        return formset.has_changed()

    def get_bound_field(self, form, field_name):
        return MultipleEmbeddedModelBoundField(form, self, field_name)


class MultipleEmbeddedModelBoundField(forms.BoundField):
    def __init__(self, form, field, name):
        super().__init__(form, field, name)
        self.formset = field.formset(
            self.data if form.is_bound else None,
            initial=models_to_dicts(self.initial),
            prefix=self.html_name,
        )

    def __str__(self):
        body = format_html_join(
            "\n", "<tbody>{}</tbody>", ((form.as_table(),) for form in self.formset)
        )
        return format_html("<table>\n{}\n</table>\n{}", body, self.formset.management_form)


class MultipleEmbeddedModelWidget(forms.Widget):
    """
    This widget extracts the data for EmbeddedModelArrayFormField's formset.
    It is never rendered.
    """

    def value_from_datadict(self, data, files, name):
        return {key: data[key] for key in data if key.startswith(f"{name}-")}
