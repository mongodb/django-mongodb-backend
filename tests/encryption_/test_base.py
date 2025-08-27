from django.test import TransactionTestCase, override_settings, skipUnlessDBFeature

from .routers import TestEncryptedRouter


@skipUnlessDBFeature("supports_queryable_encryption")
@override_settings(DATABASE_ROUTERS=[TestEncryptedRouter()])
class QueryableEncryptionTestCase(TransactionTestCase):
    databases = {"default", "encrypted"}
    available_apps = ["encryption_"]
