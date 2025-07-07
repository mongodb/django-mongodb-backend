from django.db import models


class EncryptedCharField(models.CharField):
    encrypted = True
    queries = []

    def __init__(self, *args, queries=None, **kwargs):
        self.queries = queries
        super().__init__(*args, **kwargs)
