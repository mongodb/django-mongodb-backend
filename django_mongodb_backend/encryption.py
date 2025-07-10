# Queryable Encryption helpers

from bson.binary import STANDARD
from bson.codec_options import CodecOptions
from pymongo.encryption import AutoEncryptionOpts, ClientEncryption

KEY_VAULT_COLLECTION_NAME = "__keyVault"
KEY_VAULT_DATABASE_NAME = "keyvault"
KMS_PROVIDER = "local"


class EncryptedRouter:
    """
    Routes encrypted models to their configured `db_name`,
    everything else goes to 'default'.
    """

    def _get_db_for_model(self, model):
        if getattr(model, "encrypted", False):
            return getattr(model, "db_name", "default")
        return "default"

    def db_for_read(self, model, **hints):
        return self._get_db_for_model(model)

    def db_for_write(self, model, **hints):
        return self._get_db_for_model(model)

    def allow_relation(self, obj1, obj2, **hints):
        db1 = self._get_db_for_model(obj1.__class__)
        db2 = self._get_db_for_model(obj2.__class__)
        return db1 == db2

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


def get_customer_master_key():
    """
    Returns a 96-byte local master key for use with Queryable Encryption. For
    local testing purposes only. In production, use a secure KMS like AWS,
    Azure, GCP, or KMIP.
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
    Return supported KMS providers for use with Queryable Encryption.
    """
    return {
        "local": {
            "key": get_customer_master_key(),
        },
    }
