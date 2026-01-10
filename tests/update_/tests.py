from django.db import IntegrityError
from django.test import TestCase

from .models import UniqueNumber


class UpdateTests(TestCase):
    def test_integrity_error(self):
        UniqueNumber.objects.create(number=1)
        UniqueNumber.objects.create(number=2)
        msg = "duplicate key error collection"
        with self.assertRaisesMessage(IntegrityError, msg):
            UniqueNumber.objects.filter(number=1).update(number=2)
