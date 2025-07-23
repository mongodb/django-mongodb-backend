# Queryable Encryption helper classes and settings

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
    "aws": {},
    "azure": {},
    "gcp": {},
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
