# Queryable Encryption helpers
import os

from bson.binary import STANDARD
from bson.codec_options import CodecOptions
from pymongo.encryption import AutoEncryptionOpts, ClientEncryption

KEY_VAULT_COLLECTION_NAME = "__keyVault"
KEY_VAULT_DATABASE_NAME = "keyvault"
KEY_VAULT_NAMESPACE = f"{KEY_VAULT_DATABASE_NAME}.{KEY_VAULT_COLLECTION_NAME}"
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
    # TODO: Provide a valid test key
    #
    # "Failed to parse KMS provider gcp: unable to parse base64 from UTF-8 field privateKey"
    #
    # "gcp": {
    #     "email": os.getenv("GCP_EMAIL", "not an email"),
    #     "privateKey": os.getenv("GCP_PRIVATE_KEY", "not a private key"),
    # },
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
    def _get_db_for_model(self, model):
        if getattr(model, "encrypted", False):
            return "encrypted"
        return "default"

    def db_for_read(self, model, **hints):
        return self._get_db_for_model(model)

    def db_for_write(self, model, **hints):
        return self._get_db_for_model(model)

    def allow_migrate(self, db, app_label, model_name=None, model=None, **hints):
        if model:
            return db == self._get_db_for_model(model)
        return db == "default"


class QueryType:
    """
    Class that supports building encrypted equality and range queries
    for MongoDB's Queryable Encryption.
    """

    @classmethod
    def equality(cls, *, contention=None):
        query = {"queryType": "equality"}
        if contention is not None:
            query["contention"] = contention
        return query

    @classmethod
    def range(cls, *, sparsity=None, precision=None, trimFactor=None):
        query = {"queryType": "range"}
        if sparsity is not None:
            query["sparsity"] = sparsity
        if precision is not None:
            query["precision"] = precision
        if trimFactor is not None:
            query["trimFactor"] = trimFactor
        return query


def get_auto_encryption_opts(
    *, key_vault_namespace, crypt_shared_lib_path=None, kms_providers=None, schema_map=None
):
    """
    Returns an `AutoEncryptionOpts` instance for use with Queryable Encryption.
    """
    # WARNING: Provide a schema map for production use. You can generate a schema map
    # with the management command `get_encrypted_fields_map` after adding
    # django_mongodb_backend to INSTALLED_APPS.
    return AutoEncryptionOpts(
        key_vault_namespace=key_vault_namespace,
        kms_providers=kms_providers,
        crypt_shared_lib_path=crypt_shared_lib_path,
        schema_map=schema_map,
    )


def get_client_encryption(client, key_vault_namespace=None, kms_providers=None):
    """
    Returns a `ClientEncryption` instance for use with Queryable Encryption.
    """

    codec_options = CodecOptions(uuid_representation=STANDARD)
    return ClientEncryption(kms_providers, key_vault_namespace, client, codec_options)
