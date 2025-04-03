import json

from bson import ObjectId
from django.core import serializers
from django.core.exceptions import ValidationError
from django.test import SimpleTestCase, TestCase

from django_mongodb_backend import forms
from django_mongodb_backend.fields import ObjectIdField

from .models import NullableObjectIdModel, ObjectIdModel, PrimaryKeyObjectIdModel


class MethodTests(SimpleTestCase):
    def test_deconstruct(self):
        field = ObjectIdField()
        name, path, args, kwargs = field.deconstruct()
        self.assertEqual(path, "django_mongodb_backend.fields.ObjectIdField")
        self.assertEqual(args, [])
        self.assertEqual(kwargs, {})

    def test_formfield(self):
        f = ObjectIdField().formfield()
        self.assertIsInstance(f, forms.ObjectIdField)

    def test_get_internal_type(self):
        f = ObjectIdField()
        self.assertEqual(f.get_internal_type(), "ObjectIdField")

    def test_to_python_string(self):
        value = "1" * 24
        self.assertEqual(ObjectIdField().to_python(value), ObjectId(value))

    def test_to_python_objectid(self):
        value = ObjectId("1" * 24)
        self.assertEqual(ObjectIdField().to_python(value), value)

    def test_to_python_null(self):
        self.assertIsNone(ObjectIdField().to_python(None))

    def test_to_python_invalid_value(self):
        f = ObjectIdField()
        for invalid_value in ["None", "", {}, [], 123]:
            with self.subTest(invalid_value=invalid_value):
                msg = f"['“{invalid_value}” is not a valid Object Id.']"
                with self.assertRaisesMessage(ValidationError, msg):
                    f.to_python(invalid_value)

    def test_get_prep_value_string(self):
        value = "1" * 24
        self.assertEqual(ObjectIdField().get_prep_value(value), ObjectId(value))

    def test_get_prep_value_objectid(self):
        value = ObjectId("1" * 24)
        self.assertEqual(ObjectIdField().get_prep_value(value), value)

    def test_get_prep_value_null(self):
        self.assertIsNone(ObjectIdField().get_prep_value(None))

    def test_get_prep_value_invalid_values(self):
        f = ObjectIdField()
        f.name = "test"
        for invalid_value in ["None", "", {}, [], 123]:
            with self.subTest(invalid_value=invalid_value):
                msg = f"['“{invalid_value}” is not a valid Object Id.']"
                with self.assertRaisesMessage(ValidationError, msg):
                    f.get_prep_value(invalid_value)


class SaveLoadTests(TestCase):
    def test_objectid_instance(self):
        instance = ObjectIdModel.objects.create(field=ObjectId())
        loaded = ObjectIdModel.objects.get()
        self.assertEqual(loaded.field, instance.field)

    def test_str_instance(self):
        ObjectIdModel.objects.create(field="6754ed8e584bc9ceaae3c072")
        loaded = ObjectIdModel.objects.get()
        self.assertEqual(loaded.field, ObjectId("6754ed8e584bc9ceaae3c072"))

    def test_null_handling(self):
        NullableObjectIdModel.objects.create(field=None)
        loaded = NullableObjectIdModel.objects.get()
        self.assertIsNone(loaded.field)

    def test_pk_validated(self):
        with self.assertRaisesMessage(ValidationError, "is not a valid Object Id."):
            PrimaryKeyObjectIdModel.objects.get(pk={})

        with self.assertRaisesMessage(ValidationError, "is not a valid Object Id."):
            PrimaryKeyObjectIdModel.objects.get(pk=[])

    def test_wrong_lookup_type(self):
        with self.assertRaisesMessage(ValidationError, "is not a valid Object Id."):
            ObjectIdModel.objects.get(field="not-a-objectid")

        with self.assertRaisesMessage(ValidationError, "is not a valid Object Id."):
            ObjectIdModel.objects.create(field="not-a-objectid")


class SerializationTests(TestCase):
    test_data = (
        '[{"fields": {"field": "6754ed8e584bc9ceaae3c072"}, "model": '
        '"model_fields_.objectidmodel", "pk": null}]'
    )

    def test_dumping(self):
        instance = ObjectIdModel(field=ObjectId("6754ed8e584bc9ceaae3c072"))
        data = serializers.serialize("json", [instance])
        self.assertEqual(json.loads(data), json.loads(self.test_data))

    def test_loading(self):
        instance = next(serializers.deserialize("json", self.test_data)).object
        self.assertEqual(instance.field, ObjectId("6754ed8e584bc9ceaae3c072"))


class ValidationTests(TestCase):
    def test_invalid_objectid(self):
        field = ObjectIdField()
        msg = "“550e8400” is not a valid Object Id."
        with self.assertRaisesMessage(ValidationError, msg) as cm:
            field.clean("550e8400", None)
        self.assertEqual(cm.exception.code, "invalid")

    def test_objectid_instance_ok(self):
        value = ObjectId()
        field = ObjectIdField()
        self.assertEqual(field.clean(value, None), value)
