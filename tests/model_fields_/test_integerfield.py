from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from .models import UniqueIntegers


class SmallIntegerFieldTests(TestCase):
    max_value = 2**31 - 1
    min_value = -(2**31)

    def test_unique_max_value(self):
        """
        SmallIntegerField.db_type() is "int" which means unique constraints
        are only enforced up to 32-bit values.
        """
        UniqueIntegers.objects.create(small=self.max_value + 1)
        UniqueIntegers.objects.create(small=self.max_value + 1)  # no IntegrityError
        UniqueIntegers.objects.create(small=self.max_value)
        with self.assertRaises(IntegrityError):
            UniqueIntegers.objects.create(small=self.max_value)

    def test_unique_min_value(self):
        """
        SmallIntegerField.db_type() is "int" which means unique constraints
        are only enforced down to negative 32-bit values.
        """
        UniqueIntegers.objects.create(small=self.min_value - 1)
        UniqueIntegers.objects.create(small=self.min_value - 1)  # no IntegrityError
        UniqueIntegers.objects.create(small=self.min_value)
        with self.assertRaises(IntegrityError):
            UniqueIntegers.objects.create(small=self.min_value)

    def test_validate_max_value(self):
        UniqueIntegers(small=self.max_value).full_clean()  # no error
        msg = "{'small': ['Ensure this value is less than or equal to 2147483647.']"
        with self.assertRaisesMessage(ValidationError, msg):
            UniqueIntegers(small=self.max_value + 1).full_clean()

    def test_validate_min_value(self):
        UniqueIntegers(small=self.min_value).full_clean()  # no error
        msg = "{'small': ['Ensure this value is greater than or equal to -2147483648.']"
        with self.assertRaisesMessage(ValidationError, msg):
            UniqueIntegers(small=self.min_value - 1).full_clean()


class PositiveSmallIntegerFieldTests(TestCase):
    max_value = 2**31 - 1
    min_value = 0

    def test_unique_max_value(self):
        """
        SmallIntegerField.db_type() is "int" which means unique constraints
        are only enforced up to 32-bit values.
        """
        UniqueIntegers.objects.create(positive_small=self.max_value + 1)
        UniqueIntegers.objects.create(positive_small=self.max_value + 1)  # no IntegrityError
        UniqueIntegers.objects.create(positive_small=self.max_value)
        with self.assertRaises(IntegrityError):
            UniqueIntegers.objects.create(positive_small=self.max_value)

    # test_unique_min_value isn't needed since PositiveSmallIntegerField has a
    # limit of zero (enforced only in forms and model validation).

    def test_validate_max_value(self):
        UniqueIntegers(positive_small=self.max_value).full_clean()  # no error
        msg = "{'positive_small': ['Ensure this value is less than or equal to 2147483647.']"
        with self.assertRaisesMessage(ValidationError, msg):
            UniqueIntegers(positive_small=self.max_value + 1).full_clean()

    def test_validate_min_value(self):
        UniqueIntegers(positive_small=self.min_value).full_clean()  # no error
        msg = "{'positive_small': ['Ensure this value is greater than or equal to 0.']"
        with self.assertRaisesMessage(ValidationError, msg):
            UniqueIntegers(positive_small=self.min_value - 1).full_clean()
