from zoneinfo import ZoneInfo

from django.db import NotSupportedError
from django.db.models.functions import TruncDate, TruncTime
from django.test import TestCase, override_settings

from .models import DTModel


@override_settings(USE_TZ=True)
class TruncTests(TestCase):
    melb = ZoneInfo("Australia/Melbourne")

    def test_truncdate_tzinfo(self):
        msg = "TruncDate with tzinfo (Australia/Melbourne) isn't supported on MongoDB."
        with self.assertRaisesMessage(NotSupportedError, msg):
            DTModel.objects.annotate(
                melb_date=TruncDate("start_datetime", tzinfo=self.melb),
            ).get()

    def test_trunctime_tzinfo(self):
        msg = "TruncTime with tzinfo (Australia/Melbourne) isn't supported on MongoDB."
        with self.assertRaisesMessage(NotSupportedError, msg):
            DTModel.objects.annotate(
                melb_date=TruncTime("start_datetime", tzinfo=self.melb),
            ).get()
