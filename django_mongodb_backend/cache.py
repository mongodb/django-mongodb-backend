import pickle
from datetime import datetime, timezone
from hashlib import blake2b
from typing import Any, Optional, Tuple

from django.core.cache.backends.base import DEFAULT_TIMEOUT, BaseCache
from django.core.cache.backends.db import Options
from django.core.exceptions import SuspiciousOperation
from django.db import connections, router
from django.utils.functional import cached_property
from pymongo import ASCENDING, DESCENDING, IndexModel, ReturnDocument
from pymongo.errors import DuplicateKeyError, OperationFailure
from django.conf import settings


class MongoSerializer:
    def __init__(self, protocol=None, signer=None):
        self.protocol = pickle.HIGHEST_PROTOCOL if protocol is None else protocol
        self.signer = signer

    def _get_signature(self, data) -> Optional[bytes]:
        if self.signer is None:
            return None
        s = self.signer.copy()
        s.update(data)
        return s.digest()

    def _get_pickled(self, obj: Any) -> bytes:
        return pickle.dumps(obj, protocol=self.protocol)  # noqa: S301

    def dumps(self, obj) -> Tuple[Any, bool, Optional[str]]:
        # Serialize the object to a format suitable for MongoDB storage.
        # The return value is a tuple of (data, pickled, signature).
        match obj:
            case int() | str() | bytes():
                return (obj, False, None)
            case _:
                pickled_data = self._get_pickled(obj)
                return (pickled_data, True, self._get_signature(pickled_data) if self.signer else None)

    def loads(self, data:Any, pickled:bool, signature=None) -> Any:
        if pickled:
            try:
                if self.signer is not None:
                    # constant time compare is not required due to how data is retrieved
                    if signature and (signature == self._get_signature(data)):
                        return pickle.loads(data) # noqa: S301
                    else:
                        raise SuspiciousOperation(f"Pickeled cache data is missing signature")
                else:
                    return pickle.loads(data)
            except (ValueError, TypeError):
                # ValueError: Invalid signature
                # TypeError: Data wasn't a byte string
                raise SuspiciousOperation(f'Invalid pickle signature: {{"signature": {signature}, "data":{data}}}')
        else:
            return data
                
class MongoDBCache(BaseCache):
    pickle_protocol = pickle.HIGHEST_PROTOCOL

    def __init__(self, collection_name, params):
        super().__init__(params)
        self._collection_name = collection_name

        class CacheEntry:
            _meta = Options(collection_name)

        self.cache_model_class = CacheEntry
        self._sign_cache = params.get("ENABLE_SIGNING", True)

        self._key = params.get("KEY", settings.SECRET_KEY[:64])
        if len(self._key) == 0:
            self._key = settings.SECRET_KEY[:64]
        if isinstance(self._key, str):
            self._key = self._key.encode()

        self._salt = params.get("SALT", "")
        if isinstance(self._salt, str):
            self._salt = self._salt.encode()

    def create_indexes(self):
        expires_index = IndexModel("expires_at", expireAfterSeconds=0)
        key_index = IndexModel("key", unique=True)
        self.collection_for_write.create_indexes([expires_index, key_index])

    @cached_property
    def serializer(self):
        signer = None
        if self._sign_cache:
            signer = blake2b(key=self._key[:64], salt=self._salt[:16], person=self._collection_name[:16].encode())
        return MongoSerializer(self.pickle_protocol, signer)

    @property
    def collection_for_read(self):
        db = router.db_for_read(self.cache_model_class)
        return connections[db].get_collection(self._collection_name)

    @property
    def collection_for_write(self):
        db = router.db_for_write(self.cache_model_class)
        return connections[db].get_collection(self._collection_name)

    def _filter_expired(self, expired=False):
        """
        Return MQL to exclude expired entries (needed because the MongoDB
        daemon does not remove expired entries precisely when they expire).
        If expired=True, return MQL to include only expired entries.
        """
        op = "$lt" if expired else "$gte"
        return {"expires_at": {op: datetime.utcnow()}}

    def get_backend_timeout(self, timeout=DEFAULT_TIMEOUT):
        if timeout is None:
            return datetime.max
        timestamp = super().get_backend_timeout(timeout)
        return datetime.fromtimestamp(timestamp, tz=timezone.utc)

    def get(self, key, default=None, version=None):
        return self.get_many([key], version).get(key, default)

    def get_many(self, keys, version=None):
        if not keys:
            return {}
        keys_map = {self.make_and_validate_key(key, version=version): key for key in keys}
        with self.collection_for_read.find(
            {"key": {"$in": tuple(keys_map)}, **self._filter_expired(expired=False)}
        ) as cursor:
            results = {}
            for row in cursor:
                try:
                    results[keys_map[row["key"]]] = self.serializer.loads(row["value"], row["pickled"], row["signature"])
                except SuspiciousOperation as e:
                    self.delete(row["key"])
                    e.add_note(f"Cache entry with key '{row['key']}' was deleted due to suspicious data")
                    raise e
            return results

    def set(self, key, value, timeout=DEFAULT_TIMEOUT, version=None):
        key = self.make_and_validate_key(key, version=version)
        num = self.collection_for_write.count_documents({}, hint="_id_")
        if num >= self._max_entries:
            self._cull(num)
        value, pickled, signature = self.serializer.dumps(value)
        self.collection_for_write.update_one(
            {"key": key},
            {
                "$set": {
                    "key": key,
                    "value": value,
                    "pickled": pickled,
                    "signature": signature,
                    "expires_at": self.get_backend_timeout(timeout),
                }
            },
            upsert=True,
        )

    def add(self, key, value, timeout=DEFAULT_TIMEOUT, version=None):
        key = self.make_and_validate_key(key, version=version)
        num = self.collection_for_write.count_documents({}, hint="_id_")
        if num >= self._max_entries:
            self._cull(num)
        try:
            value, pickled, signature = self.serializer.dumps(value)
            self.collection_for_write.update_one(
                {"key": key, **self._filter_expired(expired=True)},
                {
                    "$set": {
                        "key": key,
                        "value": value,
                        "pickled": pickled,
                        "signature": signature,
                        "expires_at": self.get_backend_timeout(timeout),
                    }
                },
                upsert=True,
            )
        except DuplicateKeyError:
            return False
        return True

    def _cull(self, num):
        if self._cull_frequency == 0:
            self.clear()
        else:
            # The fraction of entries that are culled when MAX_ENTRIES is
            # reached is 1 / CULL_FREQUENCY. For example, in the default case
            # of CULL_FREQUENCY=3, 2/3 of the entries are kept, thus `keep_num`
            # will be 2/3 of the current number of entries.
            keep_num = num - num // self._cull_frequency
            try:
                # Find the first cache entry beyond the retention limit,
                # culling entries that expire the soonest.
                deleted_from = next(
                    self.collection_for_write.aggregate(
                        [
                            {"$sort": {"expires_at": DESCENDING, "key": ASCENDING}},
                            {"$skip": keep_num},
                            {"$limit": 1},
                            {"$project": {"key": 1, "expires_at": 1}},
                        ]
                    )
                )
            except StopIteration:
                # If no entries are found, there is nothing to delete. It may
                # happen if the database removes expired entries between the
                # query to get `num` and the query to get `deleted_from`.
                pass
            else:
                # Cull the cache.
                self.collection_for_write.delete_many(
                    {
                        "$or": [
                            # Delete keys that expire before `deleted_from`...
                            {"expires_at": {"$lt": deleted_from["expires_at"]}},
                            # and the entries that share an expiration with
                            # `deleted_from` but are alphabetically after it
                            # (per the same sorting to fetch `deleted_from`).
                            {
                                "$and": [
                                    {"expires_at": deleted_from["expires_at"]},
                                    {"key": {"$gte": deleted_from["key"]}},
                                ]
                            },
                        ]
                    }
                )

    def touch(self, key, timeout=DEFAULT_TIMEOUT, version=None):
        key = self.make_and_validate_key(key, version=version)
        res = self.collection_for_write.update_one(
            {"key": key}, {"$set": {"expires_at": self.get_backend_timeout(timeout)}}
        )
        return res.matched_count > 0

    def incr(self, key, delta=1, version=None):
        serialized_key = self.make_and_validate_key(key, version=version)
        try:
            updated = self.collection_for_write.find_one_and_update(
                {"key": serialized_key, **self._filter_expired(expired=False)},
                {"$inc": {"value": delta}},
                return_document=ReturnDocument.AFTER,
            )
        except OperationFailure as exc:
            method_name = "incr" if delta >= 1 else "decr"
            raise TypeError(f"Cannot apply {method_name}() to a non-numeric value.") from exc
        if updated is None:
            raise ValueError(f"Key '{key}' not found.") from None
        return updated["value"]

    def delete(self, key, version=None):
        return self._delete_many([key], version)

    def delete_many(self, keys, version=None):
        self._delete_many(keys, version)

    def _delete_many(self, keys, version=None):
        if not keys:
            return False
        keys = tuple(self.make_and_validate_key(key, version=version) for key in keys)
        return bool(self.collection_for_write.delete_many({"key": {"$in": keys}}).deleted_count)

    def has_key(self, key, version=None):
        key = self.make_and_validate_key(key, version=version)
        num = self.collection_for_read.count_documents(
            {"key": key, **self._filter_expired(expired=False)}
        )
        return num > 0

    def clear(self):
        self.collection_for_write.delete_many({})
