from local_kms_encrypted_settings import *  # noqa: F403

DATABASES["encrypted"] = {  # noqa: F405
    "ENGINE": "django_mongodb_backend",
    "NAME": "djangotests_encrypted",
    "OPTIONS": {
        "auto_encryption_opts": AutoEncryptionOpts(  # noqa: F405
            key_vault_namespace="djangotests_encrypted.__keyVault",
            kms_providers={
                "aws": {
                    "accessKeyId": os.environ.get("FLE_AWS_KEY"),  # noqa: F405
                    "secretAccessKey": os.environ.get("FLE_AWS_SECRET"),  # noqa: F405
                }
            },
            crypt_shared_lib_path=os.environ["CRYPT_SHARED_LIB_PATH"],  # noqa: F405
            crypt_shared_lib_required=True,
        ),
        "directConnection": True,
    },
    "KMS_CREDENTIALS": {
        "aws": {
            "key": "arn:aws:kms:us-east-1:579766882180:key/89fcc2c4-08b0-4bd9-9f25-e30687b580d0",
            "region": "us-east-1",
        }
    },
}
