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


class SmallUniqueTests(TestCase):
    """
    Duplicate values < 32 bits are prohibited. This confirms integer field
    values are cast to Int64 so MongoDB stores it as long. Otherwise, the
    partialFilterExpression: {$type: long} unique constraint doesn't work.
    """

    test_value = 123

    def test_integerfield(self):
        UniqueIntegers.objects.create(plain=self.test_value)
        with self.assertRaises(IntegrityError):
            UniqueIntegers.objects.create(plain=self.test_value)

    def test_bigintegerfield(self):
        UniqueIntegers.objects.create(big=self.test_value)
        with self.assertRaises(IntegrityError):
            UniqueIntegers.objects.create(big=self.test_value)

    def test_positiveintegerfield(self):
        UniqueIntegers.objects.create(positive=self.test_value)
        with self.assertRaises(IntegrityError):
            UniqueIntegers.objects.create(positive=self.test_value)

    def test_positivebigintegerfield(self):
        UniqueIntegers.objects.create(positive_big=self.test_value)
        with self.assertRaises(IntegrityError):
            UniqueIntegers.objects.create(positive_big=self.test_value)


class LargeUniqueTests(TestCase):
    """
    Duplicate values > 32 bits are prohibited. This confirms each field uses
    the long db_type() rather than the 32 bit int type.
    """

    test_value = 2**63 - 1

    def test_integerfield(self):
        UniqueIntegers.objects.create(plain=self.test_value)
        with self.assertRaises(IntegrityError):
            UniqueIntegers.objects.create(plain=self.test_value)

    def test_bigintegerfield(self):
        UniqueIntegers.objects.create(big=self.test_value)
        with self.assertRaises(IntegrityError):
            UniqueIntegers.objects.create(big=self.test_value)

    def test_positiveintegerfield(self):
        UniqueIntegers.objects.create(positive=self.test_value)
        with self.assertRaises(IntegrityError):
            UniqueIntegers.objects.create(positive=self.test_value)

    def test_positivebigintegerfield(self):
        UniqueIntegers.objects.create(positive_big=self.test_value)
        with self.assertRaises(IntegrityError):
            UniqueIntegers.objects.create(positive_big=self.test_value)
