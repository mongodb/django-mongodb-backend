# Queryable Encryption helper functions and constants for MongoDB
#
# These helper functions and constants are optional and Queryable
# Encryption can be used in Django without them. They are provided
# to make it easier configure Queryable Encryption in Django.

import base64
import os

KMS_CREDENTIALS = {
    "aws": {
        "key": os.getenv("AWS_KEY_ARN", ""),
        "region": os.getenv("AWS_KEY_REGION", ""),
    },
    "azure": {
        "keyName": os.getenv("AZURE_KEY_NAME", ""),
        "keyVaultEndpoint": os.getenv("AZURE_KEY_VAULT_ENDPOINT", ""),
    },
    "gcp": {
        "projectId": os.getenv("GCP_PROJECT_ID", ""),
        "location": os.getenv("GCP_LOCATION", ""),
        "keyRing": os.getenv("GCP_KEY_RING", ""),
        "keyName": os.getenv("GCP_KEY_NAME", ""),
    },
    "kmip": {},
    "local": {},
}
KMS_PROVIDERS = {
    "aws": {
        "accessKeyId": os.getenv("AWS_ACCESS_KEY_ID", "not an access key"),
        "secretAccessKey": os.getenv("AWS_SECRET_ACCESS_KEY", "not a secret key"),
    },
    "azure": {
        "tenantId": os.getenv("AZURE_TENANT_ID", "not a tenant ID"),
        "clientId": os.getenv("AZURE_CLIENT_ID", "not a client ID"),
        "clientSecret": os.getenv("AZURE_CLIENT_SECRET", "not a client secret"),
    },
    "gcp": {
        "email": os.getenv("GCP_EMAIL", "not an email"),
        "privateKey": os.getenv(
            "GCP_PRIVATE_KEY",
            base64.b64encode(b"not a private key").decode("ascii"),
        ),
    },
    "kmip": {
        "endpoint": os.getenv("KMIP_KMS_ENDPOINT", "not a valid endpoint"),
    },
    "local": {
        "key": bytes.fromhex(
            "000102030405060708090a0b0c0d0e0f"
            "101112131415161718191a1b1c1d1e1f"
            "202122232425262728292a2b2c2d2e2f"
            "303132333435363738393a3b3c3d3e3f"
            "404142434445464748494a4b4c4d4e4f"
            "505152535455565758595a5b5c5d5e5f"
        )
    },
}


class EncryptedRouter:
    """A sample database router for Django that routes encrypted
    models to an encrypted database with a local KMS provider.
    """

    def allow_migrate(self, db, app_label, model_name=None, model=None, **hints):
        if model:
            return db == ("encrypted" if getattr(model, "encrypted", False) else "default")
        return db == "default"

    def db_for_read(self, model, **hints):
        if getattr(model, "encrypted", False):
            return "encrypted"
        return "default"

    db_for_write = db_for_read

    def kms_provider(self, model):
        return "local"


class EqualityQuery(dict):
    def __init__(self, *, contention=None):
        super().__init__(queryType="equality")
        if contention is not None:
            self["contention"] = contention


class RangeQuery(dict):
    def __init__(
        self, *, contention=None, max=None, min=None, precision=None, sparsity=None, trimFactor=None
    ):
        super().__init__(queryType="range")
        options = {
            "contention": contention,
            "max": max,
            "min": min,
            "precision": precision,
            "sparsity": sparsity,
            "trimFactor": trimFactor,
        }
        self.update({k: v for k, v in options.items() if v is not None})
