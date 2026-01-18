from bson.binary import Binary
from django.core.exceptions import ImproperlyConfigured
from django.db import NotSupportedError, connections

from . import models
from .models import EncryptionKey
from .test_base import EncryptionTestCase


class SchemaTests(EncryptionTestCase):
    def test_key_creation(self):
        """
        SchemaEditor._get_encrypted_fields() generates data encryption keys
        for the given model.
        """
        model_class = models.CharModel
        test_key_alt_name = f"{model_class._meta.db_table}.value"
        # Delete the test key and verify it's gone.
        EncryptionKey.objects.filter(key_alt_name=test_key_alt_name).delete()
        with self.assertRaises(EncryptionKey.DoesNotExist):
            EncryptionKey.objects.get(key_alt_name=test_key_alt_name)
        # Regenerate the encryption key.
        with connections["encrypted"].schema_editor() as editor:
            encrypted_fields = editor._get_encrypted_fields(model_class)
        # The schema contains the new keyId.
        field_info = encrypted_fields["fields"][0]
        self.assertEqual(field_info["path"], "value")
        self.assertIsInstance(field_info["keyId"], Binary)
        # The key vault contains the new keyId.
        key = EncryptionKey.objects.get(key_alt_name=test_key_alt_name)
        self.assertEqual(key.id, field_info["keyId"])
        self.assertEqual(key.key_alt_name, [test_key_alt_name])

    def test_missing_auto_encryption_opts(self):
        connection = connections["default"]
        msg = (
            "Tried to create model encryption_.Patient in 'default' database. "
            "The model has encrypted fields but DATABASES['default']['OPTIONS'] "
            'is missing the "auto_encryption_opts" parameter. If the model '
            "should not be created in this database, adjust your database "
            "routers."
        )
        with (
            self.assertRaisesMessage(ImproperlyConfigured, msg),
            connection.schema_editor() as editor,
        ):
            editor.create_model(models.Patient)

    def test_missing_kms_credentials(self):
        connection = connections["encrypted"]
        auto_encryption_opts = connection.connection._options.auto_encryption_opts
        kms_providers = auto_encryption_opts._kms_providers
        # Mock a GCP KMS.
        auto_encryption_opts._kms_providers = {"gcp": {}}
        # Mock the lack of KMS_CREDENTIALS.
        kms_credentials = None
        if "KMS_CREDENTIALS" in connection.settings_dict:
            kms_credentials = connection.settings_dict.pop("KMS_CREDENTIALS")
        msg = "DATABASES['encrypted'] is missing 'KMS_CREDENTIALS' required for KMS 'gcp'."
        try:
            with (
                self.assertRaisesMessage(ImproperlyConfigured, msg),
                connection.schema_editor() as editor,
            ):
                editor.create_model(models.Patient)
        finally:
            # Restore the original values.
            auto_encryption_opts._kms_providers = kms_providers
            if kms_credentials is not None:
                connection.settings_dict["KMS_CREDENTIALS"] = kms_credentials

    def test_missing_kms_credentials_entry(self):
        connection = connections["encrypted"]
        auto_encryption_opts = connection.connection._options.auto_encryption_opts
        kms_providers = auto_encryption_opts._kms_providers
        # Mock a GCP KMS.
        auto_encryption_opts._kms_providers = {"gcp": {}}
        # Mock an empty KMS_CREDENTIALS.
        kms_credentials = None
        if "KMS_CREDENTIALS" in connection.settings_dict:
            kms_credentials = connection.settings_dict.pop("KMS_CREDENTIALS")
        connection.settings_dict["KMS_CREDENTIALS"] = {}
        msg = "DATABASES['encrypted']['KMS_CREDENTIALS'] is missing 'gcp' key."
        try:
            with (
                self.assertRaisesMessage(ImproperlyConfigured, msg),
                connection.schema_editor() as editor,
            ):
                editor.create_model(models.Patient)
        finally:
            # Restore the original values.
            auto_encryption_opts._kms_providers = kms_providers
            if kms_credentials is not None:
                connection.settings_dict["KMS_CREDENTIALS"] = kms_credentials
            else:
                connection.settings_dict.pop("KMS_CREDENTIALS")

    def test_multiple_kms_providers(self):
        connection = connections["encrypted"]
        auto_encryption_opts = connection.connection._options.auto_encryption_opts
        kms_providers = auto_encryption_opts._kms_providers
        # Mock multiple kms_providers by using a list of length > 1.
        auto_encryption_opts._kms_providers = [{}, {}]
        msg = (
            "Multiple KMS providers per database aren't supported. Please "
            "create a feature request with details about your use case."
        )
        try:
            with (
                self.assertRaisesMessage(NotSupportedError, msg),
                connection.schema_editor() as editor,
            ):
                editor.create_model(models.Patient)
        finally:
            # Restore the original value.
            auto_encryption_opts._kms_providers = kms_providers
