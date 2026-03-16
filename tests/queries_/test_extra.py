from django.db import NotSupportedError
from django.test import TestCase

from .models import Author


class ExtraTests(TestCase):
    def test_where(self):
        author = Author.objects.create()
        msg = "QuerySet.extra() is not supported on MongoDB."
        with self.assertRaisesMessage(NotSupportedError, msg):
            self.assertCountEqual(Author.objects.extra(where=["id=%s"], params=[author.id]), author)
