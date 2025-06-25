from django.db import models


class EncryptedCharField(models.CharField):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.encrypted = True
