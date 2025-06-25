from django.core.checks import Error
from django.db import models
from django.test import SimpleTestCase
from django.test.utils import isolate_apps

from django_mongodb_backend.fields import (
    EmbeddedModelArrayField,
    EncryptedEmbeddedModelArrayField,
    EncryptedEmbeddedModelField,
    EncryptedIntegerField,
)
from django_mongodb_backend.models import EmbeddedModel


@isolate_apps("encryption_")
class InvalidModelsTests(SimpleTestCase):
    def test_encrypted_field_in_embedded_model_array_field(self):
        class Embedded(EmbeddedModel):
            subfield = EncryptedIntegerField()

        class Model(models.Model):
            field = EmbeddedModelArrayField(Embedded)

        self.assertEqual(
            Model.check(),
            [
                Error(
                    "EmbeddedModelArrayField cannot contain encrypted "
                    "fields (found EncryptedIntegerField).",
                    obj=Model._meta.get_field("field"),
                    id="django_mongodb_backend.embedded_model_array.E001",
                ),
            ],
        )

    def test_encrypted_field_in_encrypted_embedded_model_field(self):
        class Embedded(EmbeddedModel):
            subfield = EncryptedIntegerField()

        class Model(models.Model):
            field = EncryptedEmbeddedModelField(Embedded)

        self.assertEqual(
            Model.check(),
            [
                Error(
                    "EncryptedEmbeddedModelField cannot contain encrypted "
                    "fields (found EncryptedIntegerField).",
                    obj=Model._meta.get_field("field"),
                    id="django_mongodb_backend.embedded_model_array.E001",
                ),
            ],
        )

    def test_encrypted_field_in_encrypted_embedded_model_array_field(self):
        class Embedded(EmbeddedModel):
            subfield = EncryptedIntegerField()

        class Model(models.Model):
            field = EncryptedEmbeddedModelArrayField(Embedded)

        self.assertEqual(
            Model.check(),
            [
                Error(
                    "EncryptedEmbeddedModelArrayField cannot contain "
                    "encrypted fields (found EncryptedIntegerField).",
                    obj=Model._meta.get_field("field"),
                    id="django_mongodb_backend.embedded_model_array.E001",
                ),
            ],
        )
