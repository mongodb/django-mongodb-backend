import os

from django_mongodb_backend import parse_uri

PARSED_URI = parse_uri(os.getenv("MONGODB_URI")) if os.getenv("MONGODB_URI") else {}

# Temporary fix for https://github.com/mongodb-labs/mongo-orchestration/issues/268
if PARSED_URI.get("USER") and PARSED_URI.get("PASSWORD"):
    PARSED_URI["OPTIONS"].update({"tls": True, "tlsAllowInvalidCertificates": True})

DATABASES = {
    "default": {
        **PARSED_URI,
        "ENGINE": "django_mongodb_backend",
        "NAME": "djangotests",
    },
    "other": {
        **PARSED_URI,
        "ENGINE": "django_mongodb_backend",
        "NAME": "djangotests-other",
    },
}

DEFAULT_AUTO_FIELD = "django_mongodb_backend.fields.ObjectIdAutoField"
PASSWORD_HASHERS = ("django.contrib.auth.hashers.MD5PasswordHasher",)
SECRET_KEY = "django_tests_secret_key"
USE_TZ = False
