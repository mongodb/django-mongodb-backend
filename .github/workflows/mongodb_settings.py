import os

from pymongo.encryption_options import AutoEncryptionOpts

from django_mongodb_backend import parse_uri

if mongodb_uri := os.getenv("MONGODB_URI"):
    db_settings = parse_uri(mongodb_uri, db_name="dummy")

    # Workaround for https://github.com/mongodb-labs/mongo-orchestration/issues/268
    if db_settings["USER"] and db_settings["PASSWORD"]:
        db_settings["OPTIONS"].update({"tls": True, "tlsAllowInvalidCertificates": True})
    DATABASES = {
        "default": {**db_settings, "NAME": "djangotests"},
        "other": {**db_settings, "NAME": "djangotests-other"},
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django_mongodb_backend",
            "NAME": "djangotests",
            # Required when connecting to the Atlas image in Docker.
            "OPTIONS": {"directConnection": True},
        },
        "other": {
            "ENGINE": "django_mongodb_backend",
            "NAME": "djangotests-other",
            "OPTIONS": {"directConnection": True},
        },
    }

DATABASES["encrypted"] = {
    "ENGINE": "django_mongodb_backend",
    "NAME": "djangotests-encrypted",
    "OPTIONS": {
        "auto_encryption_opts": AutoEncryptionOpts(
            key_vault_namespace="my_encrypted_database.keyvault",
            kms_providers={"local": {"key": os.urandom(96)}},
        ),
        "directConnection": True,
    },
    "KMS_PROVIDERS": {},
    "KMS_CREDENTIALS": {},
}


class EncryptedRouter:
    def allow_migrate(self, db, app_label, model_name=None, **hints):
        # The encryption_ app's models are only created in the encrypted database.
        if app_label == "encryption_":
            return db == "encrypted"
        # Don't create other app's models in the encrypted database.
        if db == "encrypted":
            return False
        return None

    def kms_provider(self, model, **hints):
        return "local"


DATABASE_ROUTERS = [EncryptedRouter()]
DEFAULT_AUTO_FIELD = "django_mongodb_backend.fields.ObjectIdAutoField"
PASSWORD_HASHERS = ("django.contrib.auth.hashers.MD5PasswordHasher",)
SECRET_KEY = "django_tests_secret_key"
USE_TZ = False
