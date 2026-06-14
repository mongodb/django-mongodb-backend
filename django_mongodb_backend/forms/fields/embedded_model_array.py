from django import forms
from django.core.exceptions import ValidationError
from django.forms import formset_factory, model_to_dict
from django.forms.models import modelform_factory
from django.utils.html import format_html, format_html_join


class EmbeddedModelArrayField(forms.Field):
    """
    Form field for an array of embedded models, backed by a formset.

    A single bound formset instance (built in EmbeddedModelArrayBoundField) is
    the source of truth for both validation and rendering, so each per-form
    validation error renders inline next to the subfield that produced it
    instead of being aggregated onto this parent field. The formset's messages
    are still aggregated into the parent form's errors dict (so
    form.errors[name] stays meaningful), but EmbeddedModelArrayBoundField
    suppresses the per-form messages at render time to avoid showing them
    twice. Non-form errors (e.g. exceeding max_num) render once above the
    formset.
    """

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

    def _clean_bound_field(self, bf):
        formset = bf.formset
        if not formset.is_bound:
            # The field was omitted entirely; let model validation enforce
            # whether that's allowed.
            return []
        if not formset.is_valid():
            # Surface the formset's per-form and non-form messages in the
            # parent form's errors dict (so form.errors[name] stays
            # meaningful), but EmbeddedModelArrayBoundField suppresses the
            # per-form messages at render time so they aren't repeated above
            # the formset: those render inline next to each offending subfield
            # (non-form errors are rendered once, above the formset).
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
        return EmbeddedModelArrayBoundField(form, self, field_name)


class EmbeddedModelArrayBoundField(forms.BoundField):
    def __init__(self, form, field, name):
        super().__init__(form, field, name)
        # Bind the formset to the submitted data only if the user provided
        # some. html_name is the namespaced prefix in both the top-level (e.g.
        # "reviews") and nested (e.g. "products-0-reviews") cases. This single
        # formset instance is the source of truth for both validation
        # (EmbeddedModelArrayField._clean_bound_field()) and rendering
        # (__str__()); BoundField caching guarantees it's reused.
        bound = form.is_bound and bool(self.data)
        self.formset = field.formset(
            self.data if bound else None,
            initial=models_to_dicts(self.initial),
            prefix=self.html_name,
        )

    @property
    def errors(self):
        # When the formset is rendering its own per-form errors, don't also
        # render them at the parent level. Parent-level messages — e.g. the
        # whole array being required while empty, added by model validation
        # when the formset is valid — still render.
        if self.formset.is_bound and not self.formset.is_valid():
            return self.form.error_class(renderer=self.form.renderer)
        return super().errors

    def __str__(self):
        body = format_html_join(
            "\n", "<tbody>{}</tbody>", ((form.as_table(),) for form in self.formset)
        )
        # Non-form errors (e.g. "Please submit at most N forms.") aren't tied
        # to a subfield, so render them once above the formset.
        return format_html(
            "{}<table>\n{}\n</table>\n{}",
            self.formset.non_form_errors(),
            body,
            self.formset.management_form,
        )


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
