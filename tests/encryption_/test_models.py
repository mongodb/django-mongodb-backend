from django.db import NotSupportedError
from django.db.models import F

from .models import CharModel
from .test_base import EncryptionTestCase


class ModelTests(EncryptionTestCase):
    def test_update(self):
        obj = CharModel.objects.create(value="hello")
        obj.value = "updated"
        obj.save()
        obj.refresh_from_db()
        self.assertEqual(obj.value, "updated")

    def test_update_with_expression(self):
        obj = CharModel.objects.create(value="hello")
        obj.value = F("value")
        msg = "Expressions in update queries are not allowed with Queryable Encryption."
        with self.assertRaisesMessage(NotSupportedError, msg):
            obj.save()
        obj.refresh_from_db()
        self.assertEqual(obj.value, "hello")
