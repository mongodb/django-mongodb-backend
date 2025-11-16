# Settings for django_mongodb_backend/tests when encryption is supported.
import os

from mongodb_settings import *  # noqa: F403
from pymongo.encryption import AutoEncryptionOpts

os.environ["LD_LIBRARY_PATH"] = os.environ["GITHUB_WORKSPACE"] + "/lib/"

DATABASES["encrypted"] = {  # noqa: F405
    "ENGINE": "django_mongodb_backend",
    "NAME": "djangotests_encrypted",
    "OPTIONS": {
        "auto_encryption_opts": AutoEncryptionOpts(
            key_vault_namespace="djangotests_encrypted.__keyVault",
            kms_providers={"local": {"key": os.urandom(96)}},
            crypt_shared_lib_path=os.environ["GITHUB_WORKSPACE"] + "/lib/mongo_crypt_v1.so",
        ),
        "directConnection": True,
    },
    "KMS_CREDENTIALS": {},
}


class EncryptedRouter:
    def db_for_read(self, model, **hints):
        if model._meta.app_label == "encryption_":
            return "encrypted"
        return None

    db_for_write = db_for_read

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        # The encryption_ app's models are only created in the encrypted
        # database.
        if app_label == "encryption_":
            return db == "encrypted"
        # Don't create other app's models in the encrypted database.
        if db == "encrypted":
            return False
        return None


DATABASE_ROUTERS.append(EncryptedRouter())  # noqa: F405
