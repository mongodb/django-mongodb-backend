# Settings for django_mongodb_backend/tests when encryption is supported.
import os

from mongodb_settings import *  # noqa: F403
from pymongo.encryption import AutoEncryptionOpts

DATABASES["encrypted"] = {  # noqa: F405
    "ENGINE": "django_mongodb_backend",
    "NAME": "djangotests_encrypted",
    "OPTIONS": {
        "auto_encryption_opts": AutoEncryptionOpts(
            key_vault_namespace="djangotests_encrypted.__keyVault",
            kms_providers={"local": {"key": os.urandom(96)}},
            crypt_shared_lib_path=os.environ["CRYPT_SHARED_LIB_PATH"],
            crypt_shared_lib_required=True,
        ),
        "directConnection": True,
    },
}


class EncryptedRouter:
    def db_for_read(self, model, **hints):
        # All models in the encryption_ app use the encrypted database.
        if model._meta.app_label == "encryption_":
            return "encrypted"
        return None

    db_for_write = db_for_read

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        # Create the encryption_ app's models only in the encrypted database.
        if app_label == "encryption_":
            return db == "encrypted"
        # Don't create other apps' models in the encrypted database.
        if db == "encrypted":
            return False
        return None


DATABASE_ROUTERS.append(EncryptedRouter())  # noqa: F405
