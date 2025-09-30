from django.test import TestCase, skipUnlessDBFeature


@skipUnlessDBFeature("supports_queryable_encryption")
class EncryptionTestCase(TestCase):
    databases = {"default", "encrypted"}
    maxDiff = None
