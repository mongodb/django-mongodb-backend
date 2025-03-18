from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Model
from django.forms import formset_factory, model_to_dict
from django.forms.models import modelform_factory
from django.utils.html import format_html, format_html_join
from django.utils.translation import gettext_lazy as _


class MultipleEmbeddedModelFormField(forms.Field):
    default_error_messages = {"incomplete": _("Enter all required values.")}

    def __init__(self, model, prefix, max_length=None, *args, **kwargs):
        kwargs.pop("base_field")
        self.model = model
        self.prefix = prefix
        self.model_form_cls = modelform_factory(model, fields="__all__")
        self.formset = formset_factory(
            form=self.model_form_cls, can_delete=True, max_num=max_length
        )
        kwargs["widget"] = MultipleEmbeddedModelWidget(self.model_form_cls.__name__)
        super().__init__(*args, **kwargs)

    def clean(self, value):
        if not value:
            return []
        formset = self.formset(value, prefix=self.prefix)
        if not formset.is_valid():
            raise ValidationError(formset.errors + formset.non_form_errors())
        cleaned_data = []
        for data in formset.cleaned_data:
            if data.get("DELETE", True):
                continue
            data.pop("DELETE")
            cleaned_data.append(self.model_form_cls._meta.model(**data))
        return cleaned_data

    def has_changed(self, initial, data):
        formset_initial = []
        for initial_data in initial or []:
            formset_initial.append(forms.model_to_dict(initial_data))
        formset = self.formset(data, initial=formset_initial, prefix=self.prefix)
        return formset.has_changed()

    def get_bound_field(self, form, field_name):
        return MultipleEmbeddedModelBoundField(form, self, field_name)


class MultipleEmbeddedModelBoundField(forms.BoundField):
    def __init__(self, form, field, name):
        super().__init__(form, field, name)
        data = self.data if form.is_bound else None
        formset_initial = []
        if self.initial is not None:
            for initial in self.initial:
                if isinstance(initial, Model):
                    formset_initial.append(model_to_dict(initial))
        self.formset = field.formset(data, initial=formset_initial, prefix=self.html_name)

    def __getitem__(self, idx):
        if not isinstance(idx, (int | slice)):
            raise TypeError
        return self.formset[idx]

    def __iter__(self):
        yield from self.formset

    def __str__(self):
        table = format_html_join(
            "\n", "<tbody>{}</tbody>", ((form.as_table(),) for form in self.formset)
        )
        table = format_html("\n<table>" "\n{}" "\n</table>", table)
        return format_html("{}\n{}", table, self.formset.management_form)

    def __len__(self):
        return len(self.formset)


class MultipleEmbeddedModelWidget(forms.Widget):
    def __init__(self, field_id, attrs=None):
        self.field_id = field_id
        super().__init__(attrs)

    def render(self, name, value, attrs=None, renderer=None):
        raise NotImplementedError("This widget is not meant to be rendered.")

    def id_for_label(self, id_):
        return f"{id_}-0-{self.field_id}"

    def value_from_datadict(self, data, files, name):
        return {key: data[key] for key in data if key.startswith(name)}

    def value_omitted_from_data(self, data, files, name):
        return any(key.startswith(name) for key in data)
