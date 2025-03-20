from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from django_mongodb_backend.fields.validators import LengthValidator


class TestValidators(SimpleTestCase):
    def test_validators(self):
        validator = LengthValidator(10)
        with self.assertRaises(ValidationError):
            validator([])
        with self.assertRaises(ValidationError):
            validator(list(range(11)))
        self.assertEqual(validator(list(range(10))), None)
