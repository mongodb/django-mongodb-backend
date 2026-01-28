from django.db import models


class UniqueNumber(models.Model):
    number = models.IntegerField(unique=True)
