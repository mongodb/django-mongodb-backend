import pickle
from datetime import datetime, timezone

from django.core.cache.backends.base import DEFAULT_TIMEOUT, BaseCache
from django.core.cache.backends.db import Options
from django.db import connections, router
from django.utils.functional import cached_property
from pymongo.errors import DuplicateKeyError


class MongoSerializer:
    def __init__(self, protocol=None):
        self.protocol = pickle.HIGHEST_PROTOCOL if protocol is None else protocol

    def dumps(self, obj):
        if isinstance(obj, int):
            return obj
        return pickle.dumps(obj, self.protocol)

    def loads(self, data):
        try:
            return int(data)
        except (ValueError, TypeError):
            if not isinstance(data, bytes):
                raise ValueError("Invalid data type for unpickling") from None
            return pickle.loads(data)  # noqa: S301


class MongoDBCache(BaseCache):
    # This class uses collection provided by the database connection.

    pickle_protocol = pickle.HIGHEST_PROTOCOL

    def __init__(self, collection_name, params):
        super().__init__(params)
        self._collection_name = collection_name

        class CacheEntry:
            _meta = Options(collection_name)

        self.cache_model_class = CacheEntry

    def create_indexes(self):
        self.collection.create_index("expires_at", expireAfterSeconds=0)
        self.collection.create_index("key", unique=True)

    @cached_property
    def serializer(self):
        return MongoSerializer(self.pickle_protocol)

    @property
    def _db(self):
        return connections[router.db_for_read(self.cache_model_class)]

    @property
    def collection(self):
        return self._db.get_collection(self._collection_name)

    def get(self, key, default=None, version=None):
        result = self.get_many([key], version)
        if result:
            return result[key]
        return default

    def _filter_expired(self, expired=False):
        not_expired_filter = [{"expires_at": {"$gte": datetime.utcnow()}}, {"expires_at": None}]
        operator = "$nor" if expired else "$or"
        return {operator: not_expired_filter}

    def get_many(self, keys, version=None):
        if not keys:
            return {}
        keys_map = {self.make_and_validate_key(key, version=version): key for key in keys}
        with self.collection.find(
            {"key": {"$in": tuple(keys_map)}, **self._filter_expired(expired=False)}
        ) as cursor:
            return {keys_map[row["key"]]: self.serializer.loads(row["value"]) for row in cursor}

    def set(self, key, value, timeout=DEFAULT_TIMEOUT, version=None):
        key = self.make_and_validate_key(key, version=version)
        serialized_data = self.serializer.dumps(value)
        num = self.collection.count_documents({})
        if num >= self._max_entries:
            self._cull(num)
        return self.collection.update_one(
            {"key": key},
            {
                "$set": {
                    "key": key,
                    "value": serialized_data,
                    "expires_at": self._get_expiration_time(timeout),
                }
            },
            True,
        )

    def add(self, key, value, timeout=DEFAULT_TIMEOUT, version=None):
        key = self.make_and_validate_key(key, version=version)
        serialized_data = self.serializer.dumps(value)
        num = self.collection.count_documents({})
        if num >= self._max_entries:
            self._cull(num)
        try:
            self.collection.update_one(
                {"key": key, **self._filter_expired(expired=True)},
                {
                    "$set": {
                        "key": key,
                        "value": serialized_data,
                        "expires_at": self._get_expiration_time(timeout),
                    }
                },
                True,
            )
        except DuplicateKeyError:
            return False
        return True

    def _cull(self, num):
        if self._cull_frequency == 0:
            self.clear()
        else:
            keep_num = num - num // self._cull_frequency
            try:
                # Delete the first expiration date.
                deleted_from = next(
                    self.collection.aggregate(
                        [
                            {"$sort": {"expires_at": -1, "key": 1}},
                            {"$skip": keep_num},
                            {"$limit": 1},
                            {"$project": {"key": 1, "expires_at": 1}},
                        ]
                    )
                )
            except StopIteration:
                pass
            else:
                self.collection.delete_many(
                    {
                        "$or": [
                            {"expires_at": {"$lt": deleted_from["expires_at"]}},
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
        res = self.collection.update_one(
            {"key": key}, {"$set": {"expires_at": self._get_expiration_time(timeout)}}
        )
        return res.matched_count > 0

    def _get_expiration_time(self, timeout=None):
        if timeout is None:
            return None
        timestamp = self.get_backend_timeout(timeout)
        return datetime.fromtimestamp(timestamp, tz=timezone.utc)

    def delete(self, key, version=None):
        return self._delete_many([key], version)

    def delete_many(self, keys, version=None):
        self._delete_many(keys, version)

    def _delete_many(self, keys, version=None):
        if not keys:
            return False
        keys = tuple(self.make_and_validate_key(key, version=version) for key in keys)
        return bool(self.collection.delete_many({"key": {"$in": keys}}).deleted_count)

    def has_key(self, key, version=None):
        key = self.make_and_validate_key(key, version=version)
        return (
            self.collection.count_documents({"key": key, **self._filter_expired(expired=False)}) > 0
        )

    def clear(self):
        self.collection.delete_many({})
