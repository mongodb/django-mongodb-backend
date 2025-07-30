from django.db import models


class Reporter(models.Model):
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    email = models.EmailField()

    class Meta:
        ordering = ("first_name", "last_name")

    def __str__(self):
        return f"{self.first_name} {self.last_name}".strip()
