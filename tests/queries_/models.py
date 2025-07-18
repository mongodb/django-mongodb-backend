from django.db import models

from django_mongodb_backend.fields import ObjectIdAutoField, ObjectIdField


class Author(models.Model):
    name = models.CharField(max_length=10)

    def __str__(self):
        return self.name


class Book(models.Model):
    title = models.CharField(max_length=10)
    author = models.ForeignKey(Author, models.CASCADE)

    def __str__(self):
        return self.title


class Tag(models.Model):
    name = models.CharField(max_length=10)
    parent = models.ForeignKey(
        "self",
        models.SET_NULL,
        blank=True,
        null=True,
        related_name="children",
    )
    group_id = ObjectIdField(null=True)

    def __str__(self):
        return self.name


class Order(models.Model):
    id = ObjectIdAutoField(primary_key=True)
    name = models.CharField(max_length=12, null=True, default="")

    class Meta:
        ordering = ("pk",)

    def __str__(self):
        return str(self.pk)


class OrderItem(models.Model):
    order = models.ForeignKey(Order, models.CASCADE, related_name="items")
    status = ObjectIdField(null=True)

    class Meta:
        ordering = ("pk",)

    def __str__(self):
        return str(self.pk)


class Reader(models.Model):
    name = models.CharField(max_length=20)

    def __str__(self):
        return self.name


class Library(models.Model):
    name = models.CharField(max_length=20)
    readers = models.ManyToManyField(Reader, related_name="libraries")

    def __str__(self):
        return self.name
