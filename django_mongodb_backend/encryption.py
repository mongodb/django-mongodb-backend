# Queryable Encryption helpers
#
# TODO: Decide if these helpers should even exist, and if so, find a permanent
# place for them.

from bson.binary import STANDARD
from bson.codec_options import CodecOptions
from pymongo.encryption import AutoEncryptionOpts, ClientEncryption

KEY_VAULT_DATABASE_NAME = "keyvault"
KEY_VAULT_COLLECTION_NAME = "__keyVault"
KMS_PROVIDER = "local"  # e.g., "aws", "azure", "gcp", "kmip", or "local"


class EqualityQuery:
    """
    Represents an encrypted equality query for encrypted fields in MongoDB's
    Queryable Encryption.
    """

    def __init__(self, contention=None):
        self.queryType = "equality"
        self.contention = contention

    def to_dict(self):
        query_type = {"queryType": self.queryType}
        if self.contention is not None:
            query_type["contention"] = self.contention
        return [query_type]


class RangeQuery:
    """Represents an encrypted range query configuration for encrypted fields in
    MongoDB's Queryable Encryption.
    """

    def __init__(self, sparsity=None, precision=None, trimFactor=None):
        self.queryType = "range"
        self.sparsity = sparsity
        self.precision = precision
        self.trimFactor = trimFactor

    def to_dict(self):
        query_type = {"queryType": self.queryType}
        if self.sparsity is not None:
            query_type["sparsity"] = self.sparsity
        if self.precision is not None:
            query_type["precision"] = self.precision
        if self.trimFactor is not None:
            query_type["trimFactor"] = self.trimFactor
        return query_type


class QueryTypes:
    """
    Factory class for creating query type configurations for
    MongoDB Queryable Encryption.
    """

    def equality(self, *, contention=None):
        return EqualityQuery(contention=contention)

    def range(self, *, sparsity=None, precision=None, trimFactor=None):
        return RangeQuery(sparsity=sparsity, precision=precision, trimFactor=trimFactor)


def get_auto_encryption_opts(
    key_vault_namespace=None, crypt_shared_lib_path=None, kms_providers=None
):
    """
    Returns an `AutoEncryptionOpts` instance for MongoDB Client-Side Field
    Level Encryption (CSFLE) that can be used to create an encrypted connection.
    """
    return AutoEncryptionOpts(
        key_vault_namespace=key_vault_namespace,
        kms_providers=kms_providers,
        crypt_shared_lib_path=crypt_shared_lib_path,
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
