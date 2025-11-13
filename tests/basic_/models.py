from django.db import models


class Author(models.Model):
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name


class Blob(models.Model):
    name = models.CharField(max_length=10)
    data = models.JSONField(null=True)

    def __str__(self):
        return self.name
