import os

from mongodb_settings import *  # noqa: F403
from pymongo.encryption import AutoEncryptionOpts

DATABASES["encrypted"] = {  # noqa: F405
    "ENGINE": "django_mongodb_backend",
    "NAME": "djangotests_encrypted",
    "OPTIONS": {
        "auto_encryption_opts": AutoEncryptionOpts(
            key_vault_namespace="test_djangotests_encrypted.__keyVault",
            kms_providers={"local": {"key": os.urandom(96)}},
        ),
        "directConnection": True,
    },
    "KMS_CREDENTIALS": {},
}
