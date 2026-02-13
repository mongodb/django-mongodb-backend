from django.core.exceptions import ImproperlyConfigured
from django.db import NotSupportedError
from django.db.models import F

from .models import CharModel
from .test_base import EncryptionTestCase


class ModelTests(EncryptionTestCase):
    def test_create_in_non_encrypted_connection(self):
        msg = "Cannot save encrypted field 'value' in non-encrypted database 'default'."
        with self.assertRaisesMessage(ImproperlyConfigured, msg):
            CharModel.objects.using("default").create(value="value")

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
