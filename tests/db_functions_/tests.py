from django.db import NotSupportedError
from django.db.models import Func
from django.test import SimpleTestCase


class FuncTests(SimpleTestCase):
    def test_no_as_mql(self):
        msg = "Func() may need an as_mql() method."
        with self.assertRaisesMessage(NotSupportedError, msg):
            Func().as_mql(None, None)
