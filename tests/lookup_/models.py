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


class UniqueAuthor(models.Model):
    name = models.TextField(unique=True)


class UniqueBook(models.Model):
    author = models.ForeignKey(UniqueAuthor, on_delete=models.CASCADE)
    version = models.IntegerField()
    name = models.TextField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["version", "name"],
                name="unique_book_version",
            )
        ]
