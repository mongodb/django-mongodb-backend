# Settings for django_mongodb_backend/tests with AWS Key Management System.
import os

from encrypted_settings import *  # noqa: F403
from pymongo.encryption import AutoEncryptionOpts

DATABASES["encrypted"] = {  # noqa: F405
    "ENGINE": "django_mongodb_backend",
    "NAME": "djangotests_encrypted",
    "OPTIONS": {
        "auto_encryption_opts": AutoEncryptionOpts(
            key_vault_namespace="djangotests_encrypted.__keyVault",
            kms_providers={
                "aws": {
                    "accessKeyId": os.environ["AWS_ACCESS_KEY_ID"],
                    "secretAccessKey": os.environ["AWS_SECRET_ACCESS_KEY"],
                }
            },
            crypt_shared_lib_path=os.environ["CRYPT_SHARED_LIB_PATH"],
            crypt_shared_lib_required=True,
        ),
    },
    "KMS_CREDENTIALS": {
        "aws": {
            "key": os.environ["AWS_KMS_ARN"],
            "region": os.environ["AWS_DEFAULT_REGION"],
        }
    },
}
