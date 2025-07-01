from django.db import models


class EncryptedCharField(models.CharField):
    encrypted = True
