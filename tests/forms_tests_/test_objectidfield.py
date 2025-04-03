from bson import ObjectId
from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from django_mongodb_backend.forms.fields import ObjectIdField


class ObjectIdFieldTests(SimpleTestCase):
    def test_clean(self):
        field = ObjectIdField()
        value = field.clean("675747ec45260945758d76bc")
        self.assertEqual(value, ObjectId("675747ec45260945758d76bc"))

    def test_clean_objectid(self):
        field = ObjectIdField()
        value = field.clean(ObjectId("675747ec45260945758d76bc"))
        self.assertEqual(value, ObjectId("675747ec45260945758d76bc"))

    def test_clean_empty_string(self):
        field = ObjectIdField(required=False)
        value = field.clean("")
        self.assertEqual(value, None)

    def test_clean_invalid(self):
        field = ObjectIdField()
        with self.assertRaisesMessage(ValidationError, "Enter a valid Object Id."):
            field.clean("invalid")

    def test_prepare_value(self):
        field = ObjectIdField()
        value = field.prepare_value(ObjectId("675747ec45260945758d76bc"))
        self.assertEqual(value, "675747ec45260945758d76bc")
