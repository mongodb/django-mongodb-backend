import json

from bson import ObjectId, json_util
from django.test import TestCase

from .models import Author


class ExplainTests(TestCase):
    def test_idented(self):
        """The JSON is dumped with indent=4."""
        result = Author.objects.filter().explain()
        self.assertEqual(result[:23], '{\n    "explainVersion":')

    def test_object_id(self):
        """
        The json is dumped with bson.json_util() so that BSON types like ObjectID are
        specially encoded.
        """
        id = ObjectId()
        result = Author.objects.filter(id=id).explain()
        parsed = json_util.loads(result)
        self.assertEqual(
            parsed["command"]["pipeline"], [{"$match": {"$expr": {"$eq": ["$_id", id]}}}]
        )

    def test_non_ascii(self):
        """The json is dumped with ensure_ascii=False."""
        name = "\U0001d120"
        result = Author.objects.filter(name=name).explain()
        # The non-decoded string must be checked since json.loads() unescapes
        # non-ASCII characters.
        self.assertIn(name, result)
        parsed = json.loads(result)
        self.assertEqual(
            parsed["command"]["pipeline"], [{"$match": {"$expr": {"$eq": ["$name", name]}}}]
        )
