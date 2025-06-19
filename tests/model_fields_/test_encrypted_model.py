from django.test import TestCase

from .models import EncryptedData


class ModelTests(TestCase):
    def test_save_load(self):
        EncryptedData.objects.create()
