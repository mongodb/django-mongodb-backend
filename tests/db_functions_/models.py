from django.db import models


class DTModel(models.Model):
    start_datetime = models.DateTimeField(null=True, blank=True)
