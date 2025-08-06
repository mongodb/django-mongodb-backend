from datetime import timedelta

from django.db import IntegrityError
from django.test import TestCase

from .models import UniqueIntegers


class UniqueTests(TestCase):
    def test_small_value(self):
        """
        Duplicate values < 32 bits are prohibited. This confirms DurationField
        values are cast to Int64 so MongoDB stores them as long. Otherwise, the
        partialFilterExpression: {$type: long} unique constraint doesn't work.
        """
        UniqueIntegers.objects.create(duration=timedelta(1))
        with self.assertRaises(IntegrityError):
            UniqueIntegers.objects.create(duration=timedelta(1))

    def test_large_value(self):
        """
        Duplicate values > 32 bits are prohibited. This confirms DurationField
        uses the long db_type() rather than the 32 bit int type.
        """
        UniqueIntegers.objects.create(duration=timedelta(1000000))
        with self.assertRaises(IntegrityError):
            UniqueIntegers.objects.create(duration=timedelta(1000000))
