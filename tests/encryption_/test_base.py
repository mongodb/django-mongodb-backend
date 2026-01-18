from functools import reduce

import pymongo
from bson.binary import Binary
from django.conf import settings
from django.db import connections
from django.test import TestCase, skipUnlessDBFeature


@skipUnlessDBFeature("supports_queryable_encryption")
class EncryptionTestCase(TestCase):
    databases = {"default", "encrypted"}
    maxDiff = None

    def assertEncrypted(self, model, field_name):
        """
        Assert that the data in a give model's field contains binary data (and
        thus is probably encrypted).
        """
        # Create an unencrypted connection to the encrypted database.
        conn_params = connections["default"].get_connection_params()
        db_name = settings.DATABASES["encrypted"]["NAME"]
        with pymongo.MongoClient(**conn_params) as new_connection:
            db = new_connection[db_name]
            collection = db[model._meta.db_table]
            data = collection.find_one({}, {field_name: 1, "_id": 0})
            # Get the value for embedded fields (separated by dots), if
            # applicable.
            field_value = reduce(dict.__getitem__, field_name.split("."), data)
            self.assertIsInstance(field_value, Binary)
