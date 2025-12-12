import pymongo
from bson.binary import Binary
from django.conf import settings
from django.db import connections
from django.test import TestCase, skipUnlessDBFeature


@skipUnlessDBFeature("supports_queryable_encryption")
class EncryptionTestCase(TestCase):
    databases = {"default", "encrypted"}
    maxDiff = None

    def assertEncrypted(self, model, field):
        # Access encrypted database from an unencrypted connection
        conn_params = connections["default"].get_connection_params()
        db_name = settings.DATABASES["encrypted"]["NAME"]
        with pymongo.MongoClient(**conn_params) as new_connection:
            db = new_connection[db_name]
            collection = db[model._meta.db_table]
            data = collection.find_one({}, {field: 1, "_id": 0})
            self.assertIsInstance(data[field], Binary)
