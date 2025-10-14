import os

from pymongo.uri_parser import parse_uri

if mongodb_uri := os.getenv("MONGODB_URI"):
    db_settings = {
        "ENGINE": "django_mongodb_backend",
        "HOST": mongodb_uri,
    }
    # Workaround for https://github.com/mongodb-labs/mongo-orchestration/issues/268
    uri = parse_uri(mongodb_uri)
    if uri.get("username") and uri.get("password"):
        db_settings["OPTIONS"] = {"tls": True, "tlsAllowInvalidCertificates": True}
    DATABASES = {
        "default": {**db_settings, "NAME": "djangotests"},
        "other": {**db_settings, "NAME": "djangotests-other"},
        "encrypted": {},
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
        "encrypted": {},
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

    def kms_provider(self, model, **hints):
        return "local"


DATABASE_ROUTERS = [EncryptedRouter()]
DEFAULT_AUTO_FIELD = "django_mongodb_backend.fields.ObjectIdAutoField"
PASSWORD_HASHERS = ("django.contrib.auth.hashers.MD5PasswordHasher",)
SECRET_KEY = "django_tests_secret_key"
USE_TZ = False
