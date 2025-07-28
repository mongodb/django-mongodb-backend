from django import forms
from django.core import exceptions
from django.db import models
from django.test import SimpleTestCase
from django.test.utils import modify_settings
from forms_tests.widget_tests.base import WidgetTest

from django_mongodb_backend.fields import ArrayField
from django_mongodb_backend.forms import SimpleArrayField, SplitArrayField, SplitArrayWidget


class IntegerArrayModel(models.Model):
    field = ArrayField(models.IntegerField(), default=list, blank=True)


class SimpleArrayFieldTests(SimpleTestCase):
    def test_valid(self):
        field = SimpleArrayField(forms.CharField())
        value = field.clean("a,b,c")
        self.assertEqual(value, ["a", "b", "c"])

    def test_to_python_fail(self):
        field = SimpleArrayField(forms.IntegerField())
        msg = "Item 1 in the array did not validate: Enter a whole number."
        with self.assertRaisesMessage(exceptions.ValidationError, msg):
            field.clean("a,b,9")

    def test_validate_fail(self):
        field = SimpleArrayField(forms.CharField(required=True))
        msg = "Item 3 in the array did not validate: This field is required."
        with self.assertRaisesMessage(exceptions.ValidationError, msg):
            field.clean("a,b,")

    def test_validate_fail_base_field_error_params(self):
        field = SimpleArrayField(forms.CharField(max_length=2))
        with self.assertRaises(exceptions.ValidationError) as cm:
            field.clean("abc,c,defg")
        errors = cm.exception.error_list
        self.assertEqual(len(errors), 2)
        first_error = errors[0]
        self.assertEqual(
            first_error.message,
            "Item 1 in the array did not validate: Ensure this value has at most 2 "
            "characters (it has 3).",
        )
        self.assertEqual(first_error.code, "item_invalid")
        self.assertEqual(
            first_error.params,
            {"nth": 1, "value": "abc", "limit_value": 2, "show_value": 3},
        )
        second_error = errors[1]
        self.assertEqual(
            second_error.message,
            "Item 3 in the array did not validate: Ensure this value has at most 2 "
            "characters (it has 4).",
        )
        self.assertEqual(second_error.code, "item_invalid")
        self.assertEqual(
            second_error.params,
            {"nth": 3, "value": "defg", "limit_value": 2, "show_value": 4},
        )

    def test_validators_fail(self):
        field = SimpleArrayField(forms.RegexField("[a-e]{2}"))
        msg = "Item 1 in the array did not validate: Enter a valid value."
        with self.assertRaisesMessage(exceptions.ValidationError, msg):
            field.clean("a,bc,de")

    def test_delimiter(self):
        field = SimpleArrayField(forms.CharField(), delimiter="|")
        value = field.clean("a|b|c")
        self.assertEqual(value, ["a", "b", "c"])

    def test_delimiter_with_nesting(self):
        field = SimpleArrayField(SimpleArrayField(forms.CharField()), delimiter="|")
        value = field.clean("a,b|c,d")
        self.assertEqual(value, [["a", "b"], ["c", "d"]])

    def test_prepare_value(self):
        field = SimpleArrayField(forms.CharField())
        value = field.prepare_value(["a", "b", "c"])
        self.assertEqual(value, "a,b,c")

    def test_max_length(self):
        field = SimpleArrayField(forms.CharField(), max_length=2)
        msg = "List contains 3 items, it should contain no more than 2."
        with self.assertRaisesMessage(exceptions.ValidationError, msg):
            field.clean("a,b,c")

    def test_min_length(self):
        field = SimpleArrayField(forms.CharField(), min_length=4)
        msg = "List contains 3 items, it should contain no fewer than 4."
        with self.assertRaisesMessage(exceptions.ValidationError, msg):
            field.clean("a,b,c")

    def test_min_length_singular(self):
        field = SimpleArrayField(forms.IntegerField(), min_length=2)
        field.clean([1, 2])
        msg = "List contains 1 item, it should contain no fewer than 2."
        with self.assertRaisesMessage(exceptions.ValidationError, msg):
            field.clean([1])

    def test_size_length(self):
        field = SimpleArrayField(forms.CharField(max_length=27), length=4)
        msg = "List contains 3 items, it should contain 4."
        with self.assertRaisesMessage(exceptions.ValidationError, msg):
            field.clean(["a", "b", "c"])
        msg = "List contains 5 items, it should contain 4."
        with self.assertRaisesMessage(exceptions.ValidationError, msg):
            field.clean(["a", "b", "c", "d", "e"])

    def test_size_length_singular(self):
        field = SimpleArrayField(forms.CharField(max_length=27), length=4)
        msg = "List contains 1 item, it should contain 4."
        with self.assertRaisesMessage(exceptions.ValidationError, msg):
            field.clean(["a"])

    def test_required(self):
        field = SimpleArrayField(forms.CharField(), required=True)
        msg = "This field is required."
        with self.assertRaisesMessage(exceptions.ValidationError, msg):
            field.clean("")

    def test_length_and_max_min_length(self):
        msg = "The length and max_length parameters are mutually exclusive."
        with self.assertRaisesMessage(exceptions.ImproperlyConfigured, msg):
            SimpleArrayField(forms.CharField(), max_length=3, length=2)
        msg = "The length and min_length parameters are mutually exclusive."
        with self.assertRaisesMessage(exceptions.ImproperlyConfigured, msg):
            SimpleArrayField(forms.CharField(), min_length=3, length=2)

    def test_model_field_formfield(self):
        model_field = ArrayField(models.CharField(max_length=27))
        form_field = model_field.formfield()
        self.assertIsInstance(form_field, SimpleArrayField)
        self.assertIsInstance(form_field.base_field, forms.CharField)
        self.assertEqual(form_field.base_field.max_length, 27)

    def test_model_field_formfield_max_size(self):
        model_field = ArrayField(models.CharField(max_length=27), max_size=4)
        form_field = model_field.formfield()
        self.assertIsInstance(form_field, SimpleArrayField)
        self.assertEqual(form_field.max_length, 4)

    def test_model_field_formfield_size(self):
        model_field = ArrayField(models.CharField(max_length=27), size=4)
        form_field = model_field.formfield()
        self.assertIsInstance(form_field, SimpleArrayField)
        self.assertEqual(form_field.length, 4)

    def test_model_field_choices(self):
        model_field = ArrayField(models.IntegerField(choices=((1, "A"), (2, "B"))))
        form_field = model_field.formfield()
        self.assertEqual(form_field.clean("1,2"), [1, 2])

    def test_already_converted_value(self):
        field = SimpleArrayField(forms.CharField())
        vals = ["a", "b", "c"]
        self.assertEqual(field.clean(vals), vals)

    def test_has_changed(self):
        field = SimpleArrayField(forms.IntegerField())
        self.assertIs(field.has_changed([1, 2], [1, 2]), False)
        self.assertIs(field.has_changed([1, 2], "1,2"), False)
        self.assertIs(field.has_changed([1, 2], "1,2,3"), True)
        self.assertIs(field.has_changed([1, 2], "a,b"), True)

    def test_has_changed_empty(self):
        field = SimpleArrayField(forms.CharField())
        self.assertIs(field.has_changed(None, None), False)
        self.assertIs(field.has_changed(None, ""), False)
        self.assertIs(field.has_changed(None, []), False)
        self.assertIs(field.has_changed([], None), False)
        self.assertIs(field.has_changed([], ""), False)


# To locate the widget's template.
@modify_settings(INSTALLED_APPS={"append": "django_mongodb_backend"})
class SplitFormFieldTests(SimpleTestCase):
    def test_valid(self):
        class SplitForm(forms.Form):
            array = SplitArrayField(forms.CharField(), size=3)

        data = {"array_0": "a", "array_1": "b", "array_2": "c"}
        form = SplitForm(data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data, {"array": ["a", "b", "c"]})

    def test_required(self):
        class SplitForm(forms.Form):
            array = SplitArrayField(forms.CharField(), required=True, size=3)

        data = {"array_0": "", "array_1": "", "array_2": ""}
        form = SplitForm(data)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors, {"array": ["This field is required."]})

    def test_remove_trailing_nulls(self):
        class SplitForm(forms.Form):
            array = SplitArrayField(
                forms.CharField(required=False), size=5, remove_trailing_nulls=True
            )

        data = {
            "array_0": "a",
            "array_1": "",
            "array_2": "b",
            "array_3": "",
            "array_4": "",
        }
        form = SplitForm(data)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data, {"array": ["a", "", "b"]})

    def test_remove_trailing_nulls_not_required(self):
        class SplitForm(forms.Form):
            array = SplitArrayField(
                forms.CharField(required=False),
                size=2,
                remove_trailing_nulls=True,
                required=False,
            )

        data = {"array_0": "", "array_1": ""}
        form = SplitForm(data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data, {"array": []})

    def test_required_field(self):
        class SplitForm(forms.Form):
            array = SplitArrayField(forms.CharField(), size=3)

        data = {"array_0": "a", "array_1": "b", "array_2": ""}
        form = SplitForm(data)
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors,
            {"array": ["Item 3 in the array did not validate: This field is required."]},
        )

    def test_invalid_integer(self):
        msg = (
            "Item 2 in the array did not validate: Ensure this value is less than or equal to 100."
        )
        with self.assertRaisesMessage(exceptions.ValidationError, msg):
            SplitArrayField(forms.IntegerField(max_value=100), size=2).clean([0, 101])

    def test_rendering(self):
        class SplitForm(forms.Form):
            array = SplitArrayField(forms.CharField(), size=3)

        self.assertHTMLEqual(
            str(SplitForm()),
            """
            <div>
                <label for="id_array_0">Array:</label>
                <input id="id_array_0" name="array_0" type="text" required>
                <input id="id_array_1" name="array_1" type="text" required>
                <input id="id_array_2" name="array_2" type="text" required>
            </div>
        """,
        )

    def test_invalid_char_length(self):
        field = SplitArrayField(forms.CharField(max_length=2), size=3)
        with self.assertRaises(exceptions.ValidationError) as cm:
            field.clean(["abc", "c", "defg"])
        self.assertEqual(
            cm.exception.messages,
            [
                "Item 1 in the array did not validate: Ensure this value has at most 2 "
                "characters (it has 3).",
                "Item 3 in the array did not validate: Ensure this value has at most 2 "
                "characters (it has 4).",
            ],
        )

    def test_splitarraywidget_value_omitted_from_data(self):
        class Form(forms.ModelForm):
            field = SplitArrayField(forms.IntegerField(), required=False, size=2)

            class Meta:
                model = IntegerArrayModel
                fields = ("field",)

        form = Form({"field_0": "1", "field_1": "2"})
        self.assertEqual(form.errors, {})
        obj = form.save(commit=False)
        self.assertEqual(obj.field, [1, 2])

    def test_splitarrayfield_has_changed(self):
        class Form(forms.ModelForm):
            field = SplitArrayField(forms.IntegerField(), required=False, size=2)

            class Meta:
                model = IntegerArrayModel
                fields = ("field",)

        tests = [
            ({}, {"field_0": "", "field_1": ""}, True),
            ({"field": None}, {"field_0": "", "field_1": ""}, True),
            ({"field": [1]}, {"field_0": "", "field_1": ""}, True),
            ({"field": [1]}, {"field_0": "1", "field_1": "0"}, True),
            ({"field": [1, 2]}, {"field_0": "1", "field_1": "2"}, False),
            ({"field": [1, 2]}, {"field_0": "a", "field_1": "b"}, True),
        ]
        for initial, data, expected_result in tests:
            with self.subTest(initial=initial, data=data):
                obj = IntegerArrayModel(**initial)
                form = Form(data, instance=obj)
                self.assertIs(form.has_changed(), expected_result)

    def test_splitarrayfield_remove_trailing_nulls_has_changed(self):
        class Form(forms.ModelForm):
            field = SplitArrayField(
                forms.IntegerField(), required=False, size=2, remove_trailing_nulls=True
            )

            class Meta:
                model = IntegerArrayModel
                fields = ("field",)

        tests = [
            ({}, {"field_0": "", "field_1": ""}, False),
            ({"field": None}, {"field_0": "", "field_1": ""}, False),
            ({"field": []}, {"field_0": "", "field_1": ""}, False),
            ({"field": [1]}, {"field_0": "1", "field_1": ""}, False),
        ]
        for initial, data, expected_result in tests:
            with self.subTest(initial=initial, data=data):
                obj = IntegerArrayModel(**initial)
                form = Form(data, instance=obj)
                self.assertIs(form.has_changed(), expected_result)


# To locate the widget's template.
@modify_settings(INSTALLED_APPS={"append": "django_mongodb_backend"})
class SplitArrayWidgetTests(WidgetTest, SimpleTestCase):
    def test_get_context(self):
        self.assertEqual(
            SplitArrayWidget(forms.TextInput(), size=2).get_context("name", ["val1", "val2"]),
            {
                "widget": {
                    "name": "name",
                    "is_hidden": False,
                    "required": False,
                    "value": "['val1', 'val2']",
                    "attrs": {},
                    "template_name": "mongodb/widgets/split_array.html",
                    "subwidgets": [
                        {
                            "name": "name_0",
                            "is_hidden": False,
                            "required": False,
                            "value": "val1",
                            "attrs": {},
                            "template_name": "django/forms/widgets/text.html",
                            "type": "text",
                        },
                        {
                            "name": "name_1",
                            "is_hidden": False,
                            "required": False,
                            "value": "val2",
                            "attrs": {},
                            "template_name": "django/forms/widgets/text.html",
                            "type": "text",
                        },
                    ],
                }
            },
        )

    def test_checkbox_get_context_attrs(self):
        context = SplitArrayWidget(
            forms.CheckboxInput(),
            size=2,
        ).get_context("name", [True, False])
        self.assertEqual(context["widget"]["value"], "[True, False]")
        self.assertEqual(
            [subwidget["attrs"] for subwidget in context["widget"]["subwidgets"]],
            [{"checked": True}, {}],
        )

    def test_render(self):
        self.check_html(
            SplitArrayWidget(forms.TextInput(), size=2),
            "array",
            None,
            """
            <input name="array_0" type="text">
            <input name="array_1" type="text">
            """,
        )

    def test_render_attrs(self):
        self.check_html(
            SplitArrayWidget(forms.TextInput(), size=2),
            "array",
            ["val1", "val2"],
            attrs={"id": "foo"},
            html=(
                """
                <input id="foo_0" name="array_0" type="text" value="val1">
                <input id="foo_1" name="array_1" type="text" value="val2">
                """
            ),
        )

    def test_value_omitted_from_data(self):
        widget = SplitArrayWidget(forms.TextInput(), size=2)
        self.assertIs(widget.value_omitted_from_data({}, {}, "field"), True)
        self.assertIs(widget.value_omitted_from_data({"field_0": "value"}, {}, "field"), False)
        self.assertIs(widget.value_omitted_from_data({"field_1": "value"}, {}, "field"), False)
        self.assertIs(
            widget.value_omitted_from_data({"field_0": "value", "field_1": "value"}, {}, "field"),
            False,
        )
