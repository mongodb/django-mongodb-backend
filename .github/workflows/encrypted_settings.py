import os

from mongodb_settings import *  # noqa: F403
from pymongo.encryption import AutoEncryptionOpts

DATABASES["encrypted"] = {  # noqa: F405
    "ENGINE": "django_mongodb_backend",
    "NAME": "djangotests-encrypted",
    "OPTIONS": {
        "auto_encryption_opts": AutoEncryptionOpts(
            key_vault_namespace="my_encrypted_database.keyvault",
            kms_providers={"local": {"key": os.urandom(96)}},
            crypt_shared_lib_path="lib/mongo_crypt_v1.so",
        ),
        "directConnection": True,
    },
    "KMS_CREDENTIALS": {},
}
