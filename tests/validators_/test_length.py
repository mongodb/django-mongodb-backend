from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from django_mongodb_backend.validators import LengthValidator


class TestLengthValidator(SimpleTestCase):
    validator = LengthValidator(10)

    def test_empty(self):
        msg = "List contains 0 items, it should contain 10."
        with self.assertRaisesMessage(ValidationError, msg):
            self.validator([])

    def test_singular(self):
        msg = "List contains 1 item, it should contain 10."
        with self.assertRaisesMessage(ValidationError, msg):
            self.validator([1])

    def test_too_short(self):
        msg = "List contains 9 items, it should contain 10."
        with self.assertRaisesMessage(ValidationError, msg):
            self.validator([1, 2, 3, 4, 5, 6, 7, 8, 9])

    def test_too_long(self):
        msg = "List contains 11 items, it should contain 10."
        with self.assertRaisesMessage(ValidationError, msg):
            self.validator(list(range(11)))

    def test_valid(self):
        self.assertEqual(self.validator(list(range(10))), None)
