from django.core.checks import Error
from django.db import connection, models
from django.test import SimpleTestCase
from django.test.utils import isolate_apps

from django_mongodb_backend.validation import DatabaseValidation


@isolate_apps("invalid_models_tests")
class ProhibitedFieldTests(SimpleTestCase):
    def test_autofield(self):
        class Model(models.Model):
            id = models.AutoField(primary_key=True)

        field = Model._meta.get_field("id")
        validator = DatabaseValidation(connection=connection)
        self.assertEqual(
            validator.check_field(field),
            [
                Error(
                    "MongoDB does not support AutoField.",
                    hint="Use django_mongodb_backend.fields.ObjectIdAutoField instead.",
                    obj=field,
                    id="mongodb.fields.auto.E001",
                )
            ],
        )

    def test_bigautofield(self):
        class Model(models.Model):
            id = models.BigAutoField(primary_key=True)

        field = Model._meta.get_field("id")
        validator = DatabaseValidation(connection=connection)
        self.assertEqual(
            validator.check_field(field),
            [
                Error(
                    "MongoDB does not support BigAutoField.",
                    hint="Use django_mongodb_backend.fields.ObjectIdAutoField instead.",
                    obj=field,
                    id="mongodb.fields.auto.E001",
                )
            ],
        )

    def test_smallautofield(self):
        class Model(models.Model):
            id = models.SmallAutoField(primary_key=True)

        field = Model._meta.get_field("id")
        validator = DatabaseValidation(connection=connection)
        self.assertEqual(
            validator.check_field(field),
            [
                Error(
                    "MongoDB does not support SmallAutoField.",
                    hint="Use django_mongodb_backend.fields.ObjectIdAutoField instead.",
                    obj=field,
                    id="mongodb.fields.auto.E001",
                )
            ],
        )
