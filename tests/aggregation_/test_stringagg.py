from django.db import NotSupportedError
from django.db.models import StringAgg, Value
from django.test import TestCase

from .models import Author


class StringAggTests(TestCase):
    def test_not_supprted(self):
        with self.assertRaisesMessage(NotSupportedError, "StringAgg is not supported."):
            list(Author.objects.aggregate(all_names=StringAgg("name", Value(","))))
