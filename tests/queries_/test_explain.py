import json

from django.test import TestCase

from .models import Author


class ExplainTests(TestCase):
    def test_json_serializable(self):
        explain = Author.objects.all().explain()
        self.assertIsInstance(explain, str)

        explained_json = json.loads(explain)
        self.assertIsInstance(explained_json, dict)
