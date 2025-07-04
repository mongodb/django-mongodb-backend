from django.db import models


class EncryptedCharField(models.CharField):
    encrypted = True
    queries = []

    def __init__(self, *args, **kwargs):
        self.queries = kwargs.pop("queries", [])
        super().__init__(*args, **kwargs)
