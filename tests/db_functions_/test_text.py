from django.db import NotSupportedError
from django.db.models.functions import MD5, SHA256
from django.test import TestCase, skipIfDBFeature

from .models import DTModel


@skipIfDBFeature("is_mongodb_8_3")
class HashFuncTests(TestCase):
    def test_md5_requires_mongodb_8_3(self):
        msg = "MD5 requires MongoDB 8.3+."
        with self.assertRaisesMessage(NotSupportedError, msg):
            DTModel.objects.annotate(md5=MD5("start_datetime")).get()

    def test_sha256_requires_mongodb_8_3(self):
        msg = "SHA256 requires MongoDB 8.3+."
        with self.assertRaisesMessage(NotSupportedError, msg):
            DTModel.objects.annotate(sha256=SHA256("start_datetime")).get()
