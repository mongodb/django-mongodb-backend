from django_mongodb_backend.fields import EncryptedCharField
from django_mongodb_backend.models import EncryptedModel


class Person(EncryptedModel):
    ssn = EncryptedCharField("ssn", max_length=11)

    def __str__(self):
        return self.ssn
