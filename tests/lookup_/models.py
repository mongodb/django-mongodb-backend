from django.db import models


class Book(models.Model):
    title = models.CharField(max_length=10)
    isbn = models.CharField(max_length=13)

    def __str__(self):
        return self.title


class Number(models.Model):
    num = models.IntegerField(blank=True, null=True)

    class Meta:
        ordering = ("num",)

    def __str__(self):
        return str(self.num)


class UniqueFields(models.Model):
    text = models.TextField(unique=True, null=True)
    small_int = models.SmallIntegerField(unique=True, null=True)
    integer = models.IntegerField(unique=True, null=True)
    float_value = models.FloatField(unique=True, null=True)
    decimal_value = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        unique=True,
        null=True,
    )
    boolean = models.BooleanField(unique=True, null=True)
    date_value = models.DateField(unique=True, null=True)

    class Meta:
        app_label = "lookup_"
