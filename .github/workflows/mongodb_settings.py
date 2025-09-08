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

DEFAULT_AUTO_FIELD = "django_mongodb_backend.fields.ObjectIdAutoField"
PASSWORD_HASHERS = ("django.contrib.auth.hashers.MD5PasswordHasher",)
SECRET_KEY = "django_tests_secret_key"
USE_TZ = False
