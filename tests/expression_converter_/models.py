from django.db import models


class Author(models.Model):
    name = models.CharField(max_length=100)
    age = models.IntegerField()
    author_city = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Book(models.Model):
    title = models.CharField(max_length=10)
    author = models.ForeignKey(Author, models.CASCADE)

    def __str__(self):
        return self.title
