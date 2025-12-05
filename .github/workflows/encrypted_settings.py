# Settings for django_mongodb_backend/tests when encryption is supported.
import os
from pathlib import Path

from mongodb_settings import *  # noqa: F403
from pymongo.encryption import AutoEncryptionOpts

os.environ["LD_LIBRARY_PATH"] = str(Path(os.environ["CRYPT_SHARED_LIB_PATH"]).parent)

AWS_CREDS = {
    "accessKeyId": os.environ.get("FLE_AWS_KEY", ""),
    "secretAccessKey": os.environ.get("FLE_AWS_SECRET", ""),
}

_USE_AWS_KMS = any(AWS_CREDS.values())

if _USE_AWS_KMS:
    _AWS_REGION = os.environ.get("FLE_AWS_KMS_REGION", "us-east-1")
    _AWS_KEY_ARN = os.environ.get(
        "FLE_AWS_KMS_KEY_ARN",
        "arn:aws:kms:us-east-1:579766882180:key/89fcc2c4-08b0-4bd9-9f25-e30687b580d0",
    )
    KMS_PROVIDERS = {"aws": AWS_CREDS}
    KMS_CREDENTIALS = {"aws": {"key": _AWS_KEY_ARN, "region": _AWS_REGION}}
else:
    KMS_PROVIDERS = {"local": {"key": os.urandom(96)}}
    KMS_CREDENTIALS = {"local": {}}

DATABASES["encrypted"] = {  # noqa: F405
    "ENGINE": "django_mongodb_backend",
    "NAME": "djangotests_encrypted",
    "OPTIONS": {
        "auto_encryption_opts": AutoEncryptionOpts(
            key_vault_namespace="djangotests_encrypted.__keyVault",
            kms_providers=KMS_PROVIDERS,
            crypt_shared_lib_path=os.environ["CRYPT_SHARED_LIB_PATH"],
            crypt_shared_lib_required=True,
        ),
        "directConnection": True,
    },
    "KMS_CREDENTIALS": KMS_CREDENTIALS,
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
