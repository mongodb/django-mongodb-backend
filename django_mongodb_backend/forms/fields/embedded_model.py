from itertools import chain

from django import forms
from django.core.exceptions import ValidationError
from django.forms.models import modelform_factory
from django.utils.safestring import mark_safe


class EmbeddedModelField(forms.Field):
    """
    Form field for an embedded model, backed by a ModelForm.

    A single nested form instance (built in EmbeddedModelBoundField) is the
    source of truth for both validation and rendering, so each validation error
    renders inline next to the subfield that produced it instead of being
    aggregated onto this parent field. The nested form's messages are still
    aggregated into the parent form's errors dict (so form.errors[name] stays
    meaningful), but EmbeddedModelBoundField.errors suppresses them at render
    time to avoid showing them twice.
    """

    def __init__(self, model, prefix, *args, **kwargs):
        self.model = model
        # To avoid collisions with other fields on the form, each subfield is
        # prefixed with the name of this field.
        self.prefix = prefix
        self.model_form_cls = modelform_factory(model, fields="__all__")
        kwargs["widget"] = EmbeddedModelWidget(prefix)
        super().__init__(*args, **kwargs)

    def get_bound_field(self, form, field_name):
        return EmbeddedModelBoundField(form, self, field_name)

    def _clean_bound_field(self, bf):
        nested_form = bf.nested_form
        # If the user didn't submit any data, the embedded model is either
        # omitted (if allowed) or the whole field is flagged as required. In
        # neither case is there a subfield to highlight, so any message belongs
        # at the parent level.
        if not bf.has_data():
            if self.required:
                raise ValidationError(self.error_messages["required"], code="required")
            return None
        if not nested_form.is_valid():
            # Surface the nested form's per-field messages in the parent form's
            # errors dict (so form.errors[name] stays meaningful), but
            # EmbeddedModelBoundField.errors suppresses them at render time so
            # they aren't repeated at the parent level: they render inline next
            # to each offending subfield (via the bound form rendered by
            # EmbeddedModelBoundField.__str__()).
            raise ValidationError(list(chain.from_iterable(nested_form.errors.values())))
        return self.model(**nested_form.cleaned_data)


class EmbeddedModelBoundField(forms.BoundField):
    def __init__(self, form, field, name):
        super().__init__(form, field, name)
        # Nested embedded model form fields need a double prefix so that their
        # subfields are namespaced under the parent form's prefix.
        prefix = f"{form.prefix}-{field.prefix}" if form.prefix else field.prefix
        # Bind the nested model form to the submitted data only if the user
        # provided some; otherwise it's unbound so that an omitted (e.g.
        # nullable) embedded model doesn't render spurious "required" errors.
        # This single nested form instance is the source of truth for both
        # validation (EmbeddedModelField._clean_bound_field()) and rendering
        # (__str__()); BoundField caching guarantees it's reused.
        bound = form.is_bound and self.has_data()
        self.nested_form = field.model_form_cls(
            data=form.data if bound else None,
            files=form.files if bound else None,
            instance=self.initial,
            prefix=prefix,
        )

    def has_data(self):
        """Return whether the user submitted any non-empty nested data."""
        # self.data is the parent form's data filtered to this field's
        # subfields (see EmbeddedModelWidget.value_from_datadict).
        return any(self.data.values())

    @property
    def errors(self):
        # When the nested form is rendering its own per-field errors, don't
        # also render them at the parent level. Genuine parent-level messages —
        # e.g. the whole embedded model being required while empty, where the
        # nested form is unbound and has no per-field errors — still render.
        if self.nested_form.is_bound and not self.nested_form.is_valid():
            return self.form.error_class(renderer=self.form.renderer)
        return super().errors

    def __str__(self):
        """Render the (possibly bound) nested model form as this field."""
        return mark_safe(self.nested_form.as_div())  # noqa: S308


class EmbeddedModelWidget(forms.Widget):
    """
    Extract the nested form's data from the parent form's data. This widget is
    never rendered; EmbeddedModelBoundField renders the nested form instead.
    """

    # Render the field wrapped in a <fieldset> with the field's label as its
    # <legend>, grouping the nested form's subfields.
    use_fieldset = True

    def __init__(self, prefix, *args, **kwargs):
        self.prefix = prefix
        super().__init__(*args, **kwargs)

    def value_from_datadict(self, data, files, name):
        return {key: value for key, value in data.items() if key.startswith(f"{name}-")}

    def value_omitted_from_data(self, data, files, name):
        return not any(key.startswith(f"{name}-") for key in data)
