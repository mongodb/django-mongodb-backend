from django.db import models


class Number(models.Model):
    value = models.IntegerField()
