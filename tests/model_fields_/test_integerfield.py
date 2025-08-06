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


class PositiveSmallIntegerFieldTests(TestCase):
    max_value = 2**31 - 1

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
