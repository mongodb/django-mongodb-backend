import pickle
from datetime import datetime, timezone

from django.core.cache.backends.base import DEFAULT_TIMEOUT, BaseCache
from django.db import connections, router
from django.utils.functional import cached_property


class MongoSerializer:
    def __init__(self, protocol=None):
        self.protocol = pickle.HIGHEST_PROTOCOL if protocol is None else protocol

    def dumps(self, obj):
        if isinstance(obj, int):
            return obj
        try:
            return pickle.dumps(obj, self.protocol)
        except pickle.PickleError as ex:
            raise ValueError("Object cannot be pickled") from ex

    def loads(self, data):
        try:
            return int(data)
        except (ValueError, TypeError):
            if not isinstance(data, bytes):
                raise ValueError("Invalid data type for unpickling") from None
            return pickle.loads(data, fix_imports=False)  # noqa: S301


class Options:
    """A class that will quack like a Django model _meta class.

    This allows cache operations to be controlled by the router
    """

    def __init__(self, collection_name):
        self.collection_name = collection_name
        self.app_label = "django_cache"
        self.model_name = "cacheentry"
        self.verbose_name = "cache entry"
        self.verbose_name_plural = "cache entries"
        self.object_name = "CacheEntry"
        self.abstract = False
        self.managed = True
        self.proxy = False
        self.swapped = False


class BaseDatabaseCache(BaseCache):
    def __init__(self, collection_name, params):
        super().__init__(params)
        self._collection_name = collection_name

        class CacheEntry:
            _meta = Options(collection_name)

        self.cache_model_class = CacheEntry


class MongoDBCache(BaseDatabaseCache):
    def __init__(self, *args, **options):
        super().__init__(*args, **options)

    @cached_property
    def serializer(self):
        return MongoSerializer()

    @cached_property
    def collection(self):
        db = router.db_for_read(self.cache_model_class)
        return connections[db].get_collection(self._collection_name)

    def get(self, key, default=None, version=None):
        key = self.make_and_validate_key(key, version=version)
        return self.collection.find_one({"key": key}) or default

    def get_many(self, keys, version=None):
        if not keys:
            return {}
        keys_map = {self.make_and_validate_key(key, version=version): key for key in keys}
        with self.collection.find({"key": {"$in": tuple(keys_map)}}) as cursor:
            return {keys_map[row["key"]]: row["value"] for row in cursor}

    def set(self, key, value, timeout=DEFAULT_TIMEOUT, version=None):
        key = self.make_and_validate_key(key, version=version)
        serialized_data = self.serializer.dumps(value)
        return self.collection.update_one(
            {"key": key},
            {"key": key, "value": serialized_data, "expire_at": self._get_expiration_time(timeout)},
            {"upsert": True},
        )

    def add(self, key, value, timeout=DEFAULT_TIMEOUT, version=None):
        key = self.make_and_validate_key(key, version=version)
        serialized_data = self.serializer.dumps(value)
        try:
            self.collection.insert_one(
                {
                    "key": key,
                    "value": serialized_data,
                    "expire_at": self._get_expiration_time(timeout),
                }
            )
        except Exception:
            # check the exception name to catch when the key exists
            return False
        return True

    def touch(self, key, timeout=DEFAULT_TIMEOUT, version=None):
        key = self.make_and_validate_key(key, version=version)
        return self.collection.update_one(
            {"key": key}, {"$set": {"expire_at": self._get_expiration_time(timeout)}}
        )

    def _get_expiration_time(self, timeout=None):
        timestamp = self.get_backend_timeout(timeout)
        if timeout is None:
            return None
        # do I need to truncate? i don't think so.
        return datetime.fromtimestamp(timestamp, tz=timezone.utc)

    def delete(self, key, version=None):
        return self.delete_many([key], version)

    def delete_many(self, keys, version=None):
        if not keys:
            return False
        keys = [self.make_and_validate_key(key, version=version) for key in keys]
        return bool(self.collection.delete_many({"key": {"$in": tuple(keys)}}).deleted_count)

    def has_key(self, key, version=None):
        key = self.make_and_validate_key(key, version=version)
        return self.collection.count({"key": key}) > 0

    def clear(self):
        self.collection.delete_many({})
