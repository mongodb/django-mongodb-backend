from django.db import NotSupportedError
from django.db.models.expressions import Window
from django.db.models.functions.window import Rank
from django.test import TestCase

from .models import Number


class WindowTests(TestCase):
    def test_window_order_by(self):
        msg = "Window expressions must be used as annotations."
        with self.assertRaisesMessage(NotSupportedError, msg):
            list(Number.objects.order_by(Window(Rank())))
