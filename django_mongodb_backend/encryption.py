# Queryable Encryption helpers

from bson.binary import STANDARD
from bson.codec_options import CodecOptions
from django.conf import settings
from pymongo.encryption import AutoEncryptionOpts, ClientEncryption

ENCRYPTED_APPS = ["encryption_"]
ENCRYPTED_DB_ALIAS = "encrypted"
KEY_VAULT_COLLECTION_NAME = "__keyVault"
KEY_VAULT_DATABASE_NAME = "keyvault"
KMS_PROVIDER = "local"


class EncryptedRouter:
    """Do not allow migrations to the encrypted database for non-encrypted apps."""

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if db == settings.ENCRYPTED_DB_ALIAS and app_label not in settings.ENCRYPTED_APPS:
            return False
        return None


class QueryType:
    """
    Class that supports building encrypted equality and range queries
    for MongoDB's Queryable Encryption.
    """

    def __init__(self):
        self.queryType = None
        self.params = {}

    def equality(self, *, contention=None):
        obj = self.__class__.__new__(self.__class__)
        obj.queryType = "equality"
        obj.params = {"contention": contention}
        return obj

    def range(self, *, sparsity=None, precision=None, trimFactor=None):
        obj = self.__class__.__new__(self.__class__)
        obj.queryType = "range"
        obj.params = {
            "sparsity": sparsity,
            "precision": precision,
            "trimFactor": trimFactor,
        }
        return obj

    def to_dict(self):
        query = {"queryType": self.queryType}
        query.update({k: v for k, v in self.params.items() if v is not None})
        return [query] if self.queryType == "equality" else query


def get_auto_encryption_opts(
    key_vault_namespace=None, crypt_shared_lib_path=None, kms_providers=None, schema_map=None
):
    """
    Returns an `AutoEncryptionOpts` instance for MongoDB Client-Side Field
    Level Encryption (CSFLE) that can be used to create an encrypted connection.
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
    Returns a `ClientEncryption` instance for MongoDB Client-Side Field Level
    Encryption (CSFLE) that can be used to create an encrypted collection.
    """

    codec_options = CodecOptions(uuid_representation=STANDARD)
    return ClientEncryption(kms_providers, key_vault_namespace, client, codec_options)


def get_customer_master_key():
    """
    Returns a 96-byte local master key for use with MongoDB Client-Side Field Level
    Encryption (CSFLE). For local testing purposes only. In production, use a secure KMS
    like AWS, Azure, GCP, or KMIP.
    Returns:
        bytes: A 96-byte key.
    """
    # WARNING: This is a static key for testing only.
    # Generate with: os.urandom(96)
    return bytes.fromhex(
        "000102030405060708090a0b0c0d0e0f"
        "101112131415161718191a1b1c1d1e1f"
        "202122232425262728292a2b2c2d2e2f"
        "303132333435363738393a3b3c3d3e3f"
        "404142434445464748494a4b4c4d4e4f"
        "505152535455565758595a5b5c5d5e5f"
    )


def get_key_vault_namespace(
    key_vault_database_name=KEY_VAULT_DATABASE_NAME,
    key_vault_collection_name=KEY_VAULT_COLLECTION_NAME,
):
    return f"{key_vault_database_name}.{key_vault_collection_name}"


def get_kms_providers():
    """
    Return supported KMS providers for MongoDB Client-Side Field Level Encryption (CSFLE).
    """
    return {
        "local": {
            "key": get_customer_master_key(),
        },
    }
