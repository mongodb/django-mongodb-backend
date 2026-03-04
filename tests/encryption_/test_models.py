from django.core.exceptions import ImproperlyConfigured
from django.db import NotSupportedError, connections
from django.db.models import F

from .models import CharModel
from .test_base import EncryptionTestCase


class ModelTests(EncryptionTestCase):
    def test_create_in_non_encrypted_connection(self):
        connections["default"].close_pool()
        # Simulate the first connection to the database where cached properties
        # aren't initialized.
        del connections["default"].auto_encryption_opts
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

    def test_insert_collection_existence_check_cached(self):
        """
        Verify that the collection existence check for encrypted fields is
        cached and only performed once per collection.
        """
        connection = connections["encrypted"]
        # Clear the cache to start fresh
        connection._verified_encrypted_collections.clear()

        # Verify cache is empty
        self.assertNotIn(CharModel._meta.db_table, connection._verified_encrypted_collections)

        # First insert should add collection to cache
        CharModel.objects.create(value="first")
        self.assertIn(CharModel._meta.db_table, connection._verified_encrypted_collections)

        # Subsequent inserts should use the cached value
        CharModel.objects.create(value="second")
        CharModel.objects.create(value="third")
        # Cache should still contain the collection
        self.assertIn(CharModel._meta.db_table, connection._verified_encrypted_collections)
