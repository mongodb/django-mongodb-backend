from django.db import models


class Book(models.Model):
    title = models.CharField(max_length=10)

    def __str__(self):
        return self.title


class Number(models.Model):
    num = models.IntegerField(blank=True, null=True)

    class Meta:
        ordering = ("num",)

    def __str__(self):
        return str(self.num)
