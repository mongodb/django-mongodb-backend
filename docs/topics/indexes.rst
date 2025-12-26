Indexes from Expressions
========================

Django MongoDB Backend now supports creating indexes from expressions.
Currently, only ``F()`` expressions are supported, which allows referencing
fields from the top-level model inside embedded fields.

Example::

    from django.db import models
    from django.db.models import F

    class Author(models.EmbeddedModel):
        name = models.CharField()

    class Book(models.Model):
        author = models.EmbeddedField(Author)

        class Meta:
            indexes = [
                models.Index(F("author__name")),
            ]
