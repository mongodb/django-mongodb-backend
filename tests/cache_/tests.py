"""These tests are forked from Django's tests/cache/tests.py."""
import os
import pickle
import time
from functools import wraps
from unittest import mock

from bson import SON
from django.conf import settings
from django.core import management
from django.core.cache import DEFAULT_CACHE_ALIAS, CacheKeyWarning, cache, caches
from django.core.cache.backends.base import InvalidCacheBackendError
from django.http import HttpResponse
from django.middleware.cache import FetchFromCacheMiddleware, UpdateCacheMiddleware
from django.test import RequestFactory, TestCase, modify_settings, override_settings

from .models import Poll, expensive_calculation

KEY_ERRORS_WITH_MEMCACHED_MSG = (
    "Cache key contains characters that will cause errors if used with memcached: %r"
)


def f():
    return 42


class C:
    def m(n):
        return 24


class Unpicklable:
    def __getstate__(self):
        raise pickle.PickleError()


def empty_response(request):  # noqa: ARG001
    return HttpResponse()


def retry(retries=3, delay=1):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempts = 0
            while attempts < retries:
                try:
                    return func(*args, **kwargs)
                except AssertionError:
                    attempts += 1
                    if attempts >= retries:
                        raise
                    time.sleep(delay)
            return None

        return wrapper

    return decorator


def custom_key_func(key, key_prefix, version):
    "A customized cache key function"
    return "CUSTOM-" + "-".join([key_prefix, str(version), key])


_caches_setting_base = {
    "default": {},
    "prefix": {"KEY_PREFIX": f"cacheprefix{os.getpid()}"},
    "v2": {"VERSION": 2},
    "custom_key": {"KEY_FUNCTION": custom_key_func},
    "custom_key2": {"KEY_FUNCTION": "cache_.tests.custom_key_func"},
    "cull": {"OPTIONS": {"MAX_ENTRIES": 30}},
    "zero_cull": {"OPTIONS": {"CULL_FREQUENCY": 0, "MAX_ENTRIES": 30}},
}


def caches_setting_for_tests(base=None, exclude=None, **params):
    # `base` is used to pull in the memcached config from the original settings,
    # `exclude` is a set of cache names denoting which `_caches_setting_base` keys
    # should be omitted.
    # `params` are test specific overrides and `_caches_settings_base` is the
    # base config for the tests.
    # This results in the following search order:
    # params -> _caches_setting_base -> base
    base = base or {}
    exclude = exclude or set()
    setting = {k: base.copy() for k in _caches_setting_base if k not in exclude}
    for key, cache_params in setting.items():
        cache_params.update(_caches_setting_base[key])
        cache_params.update(params)
    return setting


@override_settings(
    CACHES=caches_setting_for_tests(
        BACKEND="django_mongodb_backend.cache.MongoDBCache",
        # Spaces are used in the name to ensure quoting/escaping works.
        LOCATION="test cache collection",
    ),
)
@modify_settings(
    INSTALLED_APPS={"prepend": "django_mongodb_backend"},
)
class CacheTests(TestCase):
    factory = RequestFactory()
    incr_decr_type_error_msg = "Cannot apply %s() to a non-numeric value."

    def setUp(self):
        # The super calls needs to happen first for the settings override.
        super().setUp()
        self.create_cache_collection()
        self.addCleanup(self.drop_collection)

    def create_cache_collection(self):
        management.call_command("createcachecollection", verbosity=0)

    def drop_collection(self):
        cache.collection_for_write.drop()

    def test_simple(self):
        # Simple cache set/get works
        cache.set("key", "value")
        self.assertEqual(cache.get("key"), "value")

    def test_default_used_when_none_is_set(self):
        """If None is cached, get() returns it instead of the default."""
        cache.set("key_default_none", None)
        self.assertIsNone(cache.get("key_default_none", default="default"))

    def test_add(self):
        # A key can be added to a cache
        self.assertIs(cache.add("addkey1", "value"), True)
        self.assertIs(cache.add("addkey1", "newvalue"), False)
        self.assertEqual(cache.get("addkey1"), "value")

    def test_prefix(self):
        # Test for same cache key conflicts between shared backend
        cache.set("somekey", "value")

        # should not be set in the prefixed cache
        self.assertIs(caches["prefix"].has_key("somekey"), False)

        caches["prefix"].set("somekey", "value2")

        self.assertEqual(cache.get("somekey"), "value")
        self.assertEqual(caches["prefix"].get("somekey"), "value2")

    def test_non_existent(self):
        """Nonexistent cache keys return as None/default."""
        self.assertIsNone(cache.get("does_not_exist"))
        self.assertEqual(cache.get("does_not_exist", "bang!"), "bang!")

    def test_get_many(self):
        # Multiple cache keys can be returned using get_many
        cache.set_many({"a": "a", "b": "b", "c": "c", "d": "d"})
        self.assertEqual(cache.get_many(["a", "c", "d"]), {"a": "a", "c": "c", "d": "d"})
        self.assertEqual(cache.get_many(["a", "b", "e"]), {"a": "a", "b": "b"})
        self.assertEqual(cache.get_many(iter(["a", "b", "e"])), {"a": "a", "b": "b"})
        cache.set_many({"x": None, "y": 1})
        self.assertEqual(cache.get_many(["x", "y"]), {"x": None, "y": 1})

    def test_delete(self):
        # Cache keys can be deleted
        cache.set_many({"key1": "spam", "key2": "eggs"})
        self.assertEqual(cache.get("key1"), "spam")
        self.assertIs(cache.delete("key1"), True)
        self.assertIsNone(cache.get("key1"))
        self.assertEqual(cache.get("key2"), "eggs")

    def test_delete_nonexistent(self):
        self.assertIs(cache.delete("nonexistent_key"), False)

    def test_has_key(self):
        # The cache can be inspected for cache keys
        cache.set("hello1", "goodbye1")
        self.assertIs(cache.has_key("hello1"), True)
        self.assertIs(cache.has_key("goodbye1"), False)
        cache.set("no_expiry", "here", None)
        self.assertIs(cache.has_key("no_expiry"), True)
        cache.set("null", None)
        self.assertIs(cache.has_key("null"), True)

    def test_in(self):
        # The in operator can be used to inspect cache contents
        cache.set("hello2", "goodbye2")
        self.assertIn("hello2", cache)
        self.assertNotIn("goodbye2", cache)
        cache.set("null", None)
        self.assertIn("null", cache)

    def test_incr(self):
        # Cache values can be incremented
        cache.set("answer", 41)
        self.assertEqual(cache.incr("answer"), 42)
        self.assertEqual(cache.get("answer"), 42)
        self.assertEqual(cache.incr("answer", 10), 52)
        self.assertEqual(cache.get("answer"), 52)
        self.assertEqual(cache.incr("answer", -10), 42)
        with self.assertRaisesMessage(ValueError, "Key 'does_not_exist' not found."):
            cache.incr("does_not_exist")
        with self.assertRaisesMessage(ValueError, "Key 'does_not_exist' not found."):
            cache.incr("does_not_exist", -1)
        cache.set("null", None)
        with self.assertRaisesMessage(TypeError, self.incr_decr_type_error_msg % "incr"):
            cache.incr("null")

    def test_decr(self):
        # Cache values can be decremented
        cache.set("answer", 43)
        self.assertEqual(cache.decr("answer"), 42)
        self.assertEqual(cache.get("answer"), 42)
        self.assertEqual(cache.decr("answer", 10), 32)
        self.assertEqual(cache.get("answer"), 32)
        self.assertEqual(cache.decr("answer", -10), 42)
        with self.assertRaisesMessage(ValueError, "Key 'does_not_exist' not found."):
            cache.decr("does_not_exist")
        with self.assertRaisesMessage(ValueError, "Key 'does_not_exist' not found."):
            cache.incr("does_not_exist", -1)
        cache.set("null", None)
        with self.assertRaisesMessage(TypeError, self.incr_decr_type_error_msg % "decr"):
            cache.decr("null")

    def test_close(self):
        self.assertTrue(hasattr(cache, "close"))
        cache.close()

    def test_data_types(self):
        # Many different data types can be cached
        tests = {
            "string": "this is a string",
            "int": 42,
            "bool": True,
            "list": [1, 2, 3, 4],
            "tuple": (1, 2, 3, 4),
            "dict": {"A": 1, "B": 2},
            "function": f,
            "class": C,
        }
        for key, value in tests.items():
            with self.subTest(key=key):
                cache.set(key, value)
                self.assertEqual(cache.get(key), value)

    def test_cache_read_for_model_instance(self):
        # Don't want fields with callable as default to be called on cache read
        expensive_calculation.num_runs = 0
        Poll.objects.all().delete()
        my_poll = Poll.objects.create(question="Well?")
        self.assertEqual(Poll.objects.count(), 1)
        pub_date = my_poll.pub_date
        cache.set("question", my_poll)
        cached_poll = cache.get("question")
        self.assertEqual(cached_poll.pub_date, pub_date)
        # We only want the default expensive calculation run once
        self.assertEqual(expensive_calculation.num_runs, 1)

    def test_cache_write_for_model_instance_with_deferred(self):
        # Don't want fields with callable as default to be called on cache write
        expensive_calculation.num_runs = 0
        Poll.objects.all().delete()
        Poll.objects.create(question="What?")
        self.assertEqual(expensive_calculation.num_runs, 1)
        defer_qs = Poll.objects.defer("question")
        self.assertEqual(defer_qs.count(), 1)
        self.assertEqual(expensive_calculation.num_runs, 1)
        cache.set("deferred_queryset", defer_qs)
        # cache set should not re-evaluate default functions
        self.assertEqual(expensive_calculation.num_runs, 1)

    def test_cache_read_for_model_instance_with_deferred(self):
        # Don't want fields with callable as default to be called on cache read
        expensive_calculation.num_runs = 0
        Poll.objects.all().delete()
        Poll.objects.create(question="What?")
        self.assertEqual(expensive_calculation.num_runs, 1)
        defer_qs = Poll.objects.defer("question")
        self.assertEqual(defer_qs.count(), 1)
        cache.set("deferred_queryset", defer_qs)
        self.assertEqual(expensive_calculation.num_runs, 1)
        runs_before_cache_read = expensive_calculation.num_runs
        cache.get("deferred_queryset")
        # We only want the default expensive calculation run on creation and set
        self.assertEqual(expensive_calculation.num_runs, runs_before_cache_read)

    def test_expiration(self):
        # Cache values can be set to expire
        cache.set("expire1", "very quickly", 1)
        cache.set("expire2", "very quickly", 1)
        cache.set("expire3", "very quickly", 1)

        time.sleep(2)
        self.assertIsNone(cache.get("expire1"))

        self.assertIs(cache.add("expire2", "newvalue"), True)
        self.assertEqual(cache.get("expire2"), "newvalue")
        self.assertIs(cache.has_key("expire3"), False)

    @retry()
    def test_touch(self):
        # cache.touch() updates the timeout.
        cache.set("expire1", "very quickly", timeout=1)
        self.assertIs(cache.touch("expire1", timeout=4), True)
        time.sleep(2)
        self.assertIs(cache.has_key("expire1"), True)
        time.sleep(3)
        self.assertIs(cache.has_key("expire1"), False)
        # cache.touch() works without the timeout argument.
        cache.set("expire1", "very quickly", timeout=1)
        self.assertIs(cache.touch("expire1"), True)
        time.sleep(2)
        self.assertIs(cache.has_key("expire1"), True)

        self.assertIs(cache.touch("nonexistent"), False)

    def test_unicode(self):
        # Unicode values can be cached
        stuff = {
            "ascii": "ascii_value",
            "unicode_ascii": "Iñtërnâtiônàlizætiøn1",
            "Iñtërnâtiônàlizætiøn": "Iñtërnâtiônàlizætiøn2",
            "ascii2": {"x": 1},
        }
        # Test `set`
        for key, value in stuff.items():
            with self.subTest(key=key):
                cache.set(key, value)
                self.assertEqual(cache.get(key), value)

        # Test `add`
        for key, value in stuff.items():
            with self.subTest(key=key):
                self.assertIs(cache.delete(key), True)
                self.assertIs(cache.add(key, value), True)
                self.assertEqual(cache.get(key), value)

        # Test `set_many`
        for key in stuff:
            self.assertIs(cache.delete(key), True)
        cache.set_many(stuff)
        for key, value in stuff.items():
            with self.subTest(key=key):
                self.assertEqual(cache.get(key), value)

    def test_binary_string(self):
        # Binary strings should be cacheable
        from zlib import compress, decompress

        value = "value_to_be_compressed"
        compressed_value = compress(value.encode())

        # Test set
        cache.set("binary1", compressed_value)
        compressed_result = cache.get("binary1")
        self.assertEqual(compressed_value, compressed_result)
        self.assertEqual(value, decompress(compressed_result).decode())

        # Test add
        self.assertIs(cache.add("binary1-add", compressed_value), True)
        compressed_result = cache.get("binary1-add")
        self.assertEqual(compressed_value, compressed_result)
        self.assertEqual(value, decompress(compressed_result).decode())

        # Test set_many
        cache.set_many({"binary1-set_many": compressed_value})
        compressed_result = cache.get("binary1-set_many")
        self.assertEqual(compressed_value, compressed_result)
        self.assertEqual(value, decompress(compressed_result).decode())

    def test_set_many(self):
        # Multiple keys can be set using set_many
        cache.set_many({"key1": "spam", "key2": "eggs"})
        self.assertEqual(cache.get("key1"), "spam")
        self.assertEqual(cache.get("key2"), "eggs")

    def test_set_many_returns_empty_list_on_success(self):
        """set_many() returns an empty list when all keys are inserted."""
        failing_keys = cache.set_many({"key1": "spam", "key2": "eggs"})
        self.assertEqual(failing_keys, [])

    def test_set_many_expiration(self):
        # set_many takes a second ``timeout`` parameter
        cache.set_many({"key1": "spam", "key2": "eggs"}, 1)
        time.sleep(2)
        self.assertIsNone(cache.get("key1"))
        self.assertIsNone(cache.get("key2"))

    def test_set_many_empty_data(self):
        self.assertEqual(cache.set_many({}), [])

    def test_delete_many(self):
        # Multiple keys can be deleted using delete_many
        cache.set_many({"key1": "spam", "key2": "eggs", "key3": "ham"})
        cache.delete_many(["key1", "key2"])
        self.assertIsNone(cache.get("key1"))
        self.assertIsNone(cache.get("key2"))
        self.assertEqual(cache.get("key3"), "ham")

    def test_delete_many_no_keys(self):
        self.assertIsNone(cache.delete_many([]))

    def test_clear(self):
        # The cache can be emptied using clear
        cache.set_many({"key1": "spam", "key2": "eggs"})
        cache.clear()
        self.assertIsNone(cache.get("key1"))
        self.assertIsNone(cache.get("key2"))

    def test_long_timeout(self):
        """
        Follow memcached's convention where a timeout greater than 30 days is
        treated as an absolute expiration timestamp instead of a relative
        offset (#12399).
        """
        cache.set("key1", "eggs", 60 * 60 * 24 * 30 + 1)  # 30 days + 1 second
        self.assertEqual(cache.get("key1"), "eggs")

        self.assertIs(cache.add("key2", "ham", 60 * 60 * 24 * 30 + 1), True)
        self.assertEqual(cache.get("key2"), "ham")

        cache.set_many({"key3": "sausage", "key4": "lobster bisque"}, 60 * 60 * 24 * 30 + 1)
        self.assertEqual(cache.get("key3"), "sausage")
        self.assertEqual(cache.get("key4"), "lobster bisque")

    @retry()
    def test_forever_timeout(self):
        """
        Passing in None into timeout results in a value that is cached forever
        """
        cache.set("key1", "eggs", None)
        self.assertEqual(cache.get("key1"), "eggs")

        self.assertIs(cache.add("key2", "ham", None), True)
        self.assertEqual(cache.get("key2"), "ham")
        self.assertIs(cache.add("key1", "new eggs", None), False)
        self.assertEqual(cache.get("key1"), "eggs")

        cache.set_many({"key3": "sausage", "key4": "lobster bisque"}, None)
        self.assertEqual(cache.get("key3"), "sausage")
        self.assertEqual(cache.get("key4"), "lobster bisque")

        cache.set("key5", "belgian fries", timeout=1)
        self.assertIs(cache.touch("key5", timeout=None), True)
        time.sleep(2)
        self.assertEqual(cache.get("key5"), "belgian fries")

    def test_zero_timeout(self):
        """
        Passing in zero into timeout results in a value that is not cached
        """
        cache.set("key1", "eggs", 0)
        self.assertIsNone(cache.get("key1"))

        self.assertIs(cache.add("key2", "ham", 0), True)
        self.assertIsNone(cache.get("key2"))

        cache.set_many({"key3": "sausage", "key4": "lobster bisque"}, 0)
        self.assertIsNone(cache.get("key3"))
        self.assertIsNone(cache.get("key4"))

        cache.set("key5", "belgian fries", timeout=5)
        self.assertIs(cache.touch("key5", timeout=0), True)
        self.assertIsNone(cache.get("key5"))

    def test_float_timeout(self):
        # Make sure a timeout given as a float doesn't crash anything.
        cache.set("key1", "spam", 100.2)
        self.assertEqual(cache.get("key1"), "spam")

    def _perform_cull_test(self, cull_cache_name, initial_count, final_count):
        try:
            cull_cache = caches[cull_cache_name]
        except InvalidCacheBackendError:
            self.skipTest("Culling isn't implemented.")

        # Create initial cache key entries. This will overflow the cache,
        # causing a cull.
        for i in range(1, initial_count):
            cull_cache.set("cull%d" % i, "value", 1000)
        count = 0
        # Count how many keys are left in the cache.
        for i in range(1, initial_count):
            if cull_cache.has_key("cull%d" % i):
                count += 1
        self.assertEqual(count, final_count)

    def test_cull(self):
        self._perform_cull_test("cull", 50, 29)

    def test_zero_cull(self):
        self._perform_cull_test("zero_cull", 50, 19)

    def test_cull_delete_when_store_empty(self):
        try:
            cull_cache = caches["cull"]
        except InvalidCacheBackendError:
            self.skipTest("Culling isn't implemented.")
        old_max_entries = cull_cache._max_entries
        # Force _cull to delete on first cached record.
        cull_cache._max_entries = -1
        try:
            cull_cache.set("force_cull_delete", "value", 1000)
            self.assertIs(cull_cache.has_key("force_cull_delete"), True)
        finally:
            cull_cache._max_entries = old_max_entries

    def _perform_invalid_key_test(self, key, expected_warning, key_func=None):
        """
        All the builtin backends should warn (except memcached that should
        error) on keys that would be refused by memcached. This encourages
        portable caching code without making it too difficult to use production
        backends with more liberal key rules. Refs #6447.
        """

        # mimic custom ``make_key`` method being defined since the default will
        # never show the below warnings
        def func(key, *args):  # noqa: ARG001
            return key

        old_func = cache.key_func
        cache.key_func = key_func or func

        tests = [
            ("add", [key, 1]),
            ("get", [key]),
            ("set", [key, 1]),
            ("incr", [key]),
            ("decr", [key]),
            ("touch", [key]),
            ("delete", [key]),
            ("get_many", [[key, "b"]]),
            ("set_many", [{key: 1, "b": 2}]),
            ("delete_many", [[key, "b"]]),
        ]
        try:
            for operation, args in tests:
                with self.subTest(operation=operation):
                    with self.assertWarns(CacheKeyWarning) as cm:
                        getattr(cache, operation)(*args)
                    self.assertEqual(str(cm.warning), expected_warning)
        finally:
            cache.key_func = old_func

    def test_invalid_key_characters(self):
        # memcached doesn't allow whitespace or control characters in keys.
        key = "key with spaces and 清"
        self._perform_invalid_key_test(key, KEY_ERRORS_WITH_MEMCACHED_MSG % key)

    def test_invalid_key_length(self):
        # memcached limits key length to 250.
        key = ("a" * 250) + "清"
        expected_warning = (
            "Cache key will cause errors if used with memcached: " f"'{key}' (longer than 250)"
        )
        self._perform_invalid_key_test(key, expected_warning)

    def test_invalid_with_version_key_length(self):
        # Custom make_key() that adds a version to the key and exceeds the
        # limit.
        def key_func(key, *args):  # noqa: ARG001
            return key + ":1"

        key = "a" * 249
        expected_warning = (
            "Cache key will cause errors if used with memcached: "
            f"'{key_func(key)}' (longer than 250)"
        )
        self._perform_invalid_key_test(key, expected_warning, key_func=key_func)

    def test_cache_versioning_get_set(self):
        # set, using default version = 1
        cache.set("answer1", 42)
        self.assertEqual(cache.get("answer1"), 42)
        self.assertEqual(cache.get("answer1", version=1), 42)
        self.assertIsNone(cache.get("answer1", version=2))

        self.assertIsNone(caches["v2"].get("answer1"))
        self.assertEqual(caches["v2"].get("answer1", version=1), 42)
        self.assertIsNone(caches["v2"].get("answer1", version=2))

        # set, default version = 1, but manually override version = 2
        cache.set("answer2", 42, version=2)
        self.assertIsNone(cache.get("answer2"))
        self.assertIsNone(cache.get("answer2", version=1))
        self.assertEqual(cache.get("answer2", version=2), 42)

        self.assertEqual(caches["v2"].get("answer2"), 42)
        self.assertIsNone(caches["v2"].get("answer2", version=1))
        self.assertEqual(caches["v2"].get("answer2", version=2), 42)

        # v2 set, using default version = 2
        caches["v2"].set("answer3", 42)
        self.assertIsNone(cache.get("answer3"))
        self.assertIsNone(cache.get("answer3", version=1))
        self.assertEqual(cache.get("answer3", version=2), 42)

        self.assertEqual(caches["v2"].get("answer3"), 42)
        self.assertIsNone(caches["v2"].get("answer3", version=1))
        self.assertEqual(caches["v2"].get("answer3", version=2), 42)

        # v2 set, default version = 2, but manually override version = 1
        caches["v2"].set("answer4", 42, version=1)
        self.assertEqual(cache.get("answer4"), 42)
        self.assertEqual(cache.get("answer4", version=1), 42)
        self.assertIsNone(cache.get("answer4", version=2))

        self.assertIsNone(caches["v2"].get("answer4"))
        self.assertEqual(caches["v2"].get("answer4", version=1), 42)
        self.assertIsNone(caches["v2"].get("answer4", version=2))

    def test_cache_versioning_add(self):
        # add, default version = 1, but manually override version = 2
        self.assertIs(cache.add("answer1", 42, version=2), True)
        self.assertIsNone(cache.get("answer1", version=1))
        self.assertEqual(cache.get("answer1", version=2), 42)

        self.assertIs(cache.add("answer1", 37, version=2), False)
        self.assertIsNone(cache.get("answer1", version=1))
        self.assertEqual(cache.get("answer1", version=2), 42)

        self.assertIs(cache.add("answer1", 37, version=1), True)
        self.assertEqual(cache.get("answer1", version=1), 37)
        self.assertEqual(cache.get("answer1", version=2), 42)

        # v2 add, using default version = 2
        self.assertIs(caches["v2"].add("answer2", 42), True)
        self.assertIsNone(cache.get("answer2", version=1))
        self.assertEqual(cache.get("answer2", version=2), 42)

        self.assertIs(caches["v2"].add("answer2", 37), False)
        self.assertIsNone(cache.get("answer2", version=1))
        self.assertEqual(cache.get("answer2", version=2), 42)

        self.assertIs(caches["v2"].add("answer2", 37, version=1), True)
        self.assertEqual(cache.get("answer2", version=1), 37)
        self.assertEqual(cache.get("answer2", version=2), 42)

        # v2 add, default version = 2, but manually override version = 1
        self.assertIs(caches["v2"].add("answer3", 42, version=1), True)
        self.assertEqual(cache.get("answer3", version=1), 42)
        self.assertIsNone(cache.get("answer3", version=2))

        self.assertIs(caches["v2"].add("answer3", 37, version=1), False)
        self.assertEqual(cache.get("answer3", version=1), 42)
        self.assertIsNone(cache.get("answer3", version=2))

        self.assertIs(caches["v2"].add("answer3", 37), True)
        self.assertEqual(cache.get("answer3", version=1), 42)
        self.assertEqual(cache.get("answer3", version=2), 37)

    def test_cache_versioning_has_key(self):
        cache.set("answer1", 42)

        # has_key
        self.assertIs(cache.has_key("answer1"), True)
        self.assertIs(cache.has_key("answer1", version=1), True)
        self.assertIs(cache.has_key("answer1", version=2), False)

        self.assertIs(caches["v2"].has_key("answer1"), False)
        self.assertIs(caches["v2"].has_key("answer1", version=1), True)
        self.assertIs(caches["v2"].has_key("answer1", version=2), False)

    def test_cache_versioning_delete(self):
        cache.set("answer1", 37, version=1)
        cache.set("answer1", 42, version=2)
        self.assertIs(cache.delete("answer1"), True)
        self.assertIsNone(cache.get("answer1", version=1))
        self.assertEqual(cache.get("answer1", version=2), 42)

        cache.set("answer2", 37, version=1)
        cache.set("answer2", 42, version=2)
        self.assertIs(cache.delete("answer2", version=2), True)
        self.assertEqual(cache.get("answer2", version=1), 37)
        self.assertIsNone(cache.get("answer2", version=2))

        cache.set("answer3", 37, version=1)
        cache.set("answer3", 42, version=2)
        self.assertIs(caches["v2"].delete("answer3"), True)
        self.assertEqual(cache.get("answer3", version=1), 37)
        self.assertIsNone(cache.get("answer3", version=2))

        cache.set("answer4", 37, version=1)
        cache.set("answer4", 42, version=2)
        self.assertIs(caches["v2"].delete("answer4", version=1), True)
        self.assertIsNone(cache.get("answer4", version=1))
        self.assertEqual(cache.get("answer4", version=2), 42)

    def test_cache_versioning_incr_decr(self):
        cache.set("answer1", 37, version=1)
        cache.set("answer1", 42, version=2)
        self.assertEqual(cache.incr("answer1"), 38)
        self.assertEqual(cache.get("answer1", version=1), 38)
        self.assertEqual(cache.get("answer1", version=2), 42)
        self.assertEqual(cache.decr("answer1"), 37)
        self.assertEqual(cache.get("answer1", version=1), 37)
        self.assertEqual(cache.get("answer1", version=2), 42)

        cache.set("answer2", 37, version=1)
        cache.set("answer2", 42, version=2)
        self.assertEqual(cache.incr("answer2", version=2), 43)
        self.assertEqual(cache.get("answer2", version=1), 37)
        self.assertEqual(cache.get("answer2", version=2), 43)
        self.assertEqual(cache.decr("answer2", version=2), 42)
        self.assertEqual(cache.get("answer2", version=1), 37)
        self.assertEqual(cache.get("answer2", version=2), 42)

        cache.set("answer3", 37, version=1)
        cache.set("answer3", 42, version=2)
        self.assertEqual(caches["v2"].incr("answer3"), 43)
        self.assertEqual(cache.get("answer3", version=1), 37)
        self.assertEqual(cache.get("answer3", version=2), 43)
        self.assertEqual(caches["v2"].decr("answer3"), 42)
        self.assertEqual(cache.get("answer3", version=1), 37)
        self.assertEqual(cache.get("answer3", version=2), 42)

        cache.set("answer4", 37, version=1)
        cache.set("answer4", 42, version=2)
        self.assertEqual(caches["v2"].incr("answer4", version=1), 38)
        self.assertEqual(cache.get("answer4", version=1), 38)
        self.assertEqual(cache.get("answer4", version=2), 42)
        self.assertEqual(caches["v2"].decr("answer4", version=1), 37)
        self.assertEqual(cache.get("answer4", version=1), 37)
        self.assertEqual(cache.get("answer4", version=2), 42)

    def test_cache_versioning_get_set_many(self):
        # set, using default version = 1
        cache.set_many({"ford1": 37, "arthur1": 42})
        self.assertEqual(cache.get_many(["ford1", "arthur1"]), {"ford1": 37, "arthur1": 42})
        self.assertEqual(
            cache.get_many(["ford1", "arthur1"], version=1),
            {"ford1": 37, "arthur1": 42},
        )
        self.assertEqual(cache.get_many(["ford1", "arthur1"], version=2), {})

        self.assertEqual(caches["v2"].get_many(["ford1", "arthur1"]), {})
        self.assertEqual(
            caches["v2"].get_many(["ford1", "arthur1"], version=1),
            {"ford1": 37, "arthur1": 42},
        )
        self.assertEqual(caches["v2"].get_many(["ford1", "arthur1"], version=2), {})

        # set, default version = 1, but manually override version = 2
        cache.set_many({"ford2": 37, "arthur2": 42}, version=2)
        self.assertEqual(cache.get_many(["ford2", "arthur2"]), {})
        self.assertEqual(cache.get_many(["ford2", "arthur2"], version=1), {})
        self.assertEqual(
            cache.get_many(["ford2", "arthur2"], version=2),
            {"ford2": 37, "arthur2": 42},
        )

        self.assertEqual(caches["v2"].get_many(["ford2", "arthur2"]), {"ford2": 37, "arthur2": 42})
        self.assertEqual(caches["v2"].get_many(["ford2", "arthur2"], version=1), {})
        self.assertEqual(
            caches["v2"].get_many(["ford2", "arthur2"], version=2),
            {"ford2": 37, "arthur2": 42},
        )

        # v2 set, using default version = 2
        caches["v2"].set_many({"ford3": 37, "arthur3": 42})
        self.assertEqual(cache.get_many(["ford3", "arthur3"]), {})
        self.assertEqual(cache.get_many(["ford3", "arthur3"], version=1), {})
        self.assertEqual(
            cache.get_many(["ford3", "arthur3"], version=2),
            {"ford3": 37, "arthur3": 42},
        )

        self.assertEqual(caches["v2"].get_many(["ford3", "arthur3"]), {"ford3": 37, "arthur3": 42})
        self.assertEqual(caches["v2"].get_many(["ford3", "arthur3"], version=1), {})
        self.assertEqual(
            caches["v2"].get_many(["ford3", "arthur3"], version=2),
            {"ford3": 37, "arthur3": 42},
        )

        # v2 set, default version = 2, but manually override version = 1
        caches["v2"].set_many({"ford4": 37, "arthur4": 42}, version=1)
        self.assertEqual(cache.get_many(["ford4", "arthur4"]), {"ford4": 37, "arthur4": 42})
        self.assertEqual(
            cache.get_many(["ford4", "arthur4"], version=1),
            {"ford4": 37, "arthur4": 42},
        )
        self.assertEqual(cache.get_many(["ford4", "arthur4"], version=2), {})

        self.assertEqual(caches["v2"].get_many(["ford4", "arthur4"]), {})
        self.assertEqual(
            caches["v2"].get_many(["ford4", "arthur4"], version=1),
            {"ford4": 37, "arthur4": 42},
        )
        self.assertEqual(caches["v2"].get_many(["ford4", "arthur4"], version=2), {})

    def test_incr_version(self):
        cache.set("answer", 42, version=2)
        self.assertIsNone(cache.get("answer"))
        self.assertIsNone(cache.get("answer", version=1))
        self.assertEqual(cache.get("answer", version=2), 42)
        self.assertIsNone(cache.get("answer", version=3))

        self.assertEqual(cache.incr_version("answer", version=2), 3)
        self.assertIsNone(cache.get("answer"))
        self.assertIsNone(cache.get("answer", version=1))
        self.assertIsNone(cache.get("answer", version=2))
        self.assertEqual(cache.get("answer", version=3), 42)

        caches["v2"].set("answer2", 42)
        self.assertEqual(caches["v2"].get("answer2"), 42)
        self.assertIsNone(caches["v2"].get("answer2", version=1))
        self.assertEqual(caches["v2"].get("answer2", version=2), 42)
        self.assertIsNone(caches["v2"].get("answer2", version=3))

        self.assertEqual(caches["v2"].incr_version("answer2"), 3)
        self.assertIsNone(caches["v2"].get("answer2"))
        self.assertIsNone(caches["v2"].get("answer2", version=1))
        self.assertIsNone(caches["v2"].get("answer2", version=2))
        self.assertEqual(caches["v2"].get("answer2", version=3), 42)

        with self.assertRaises(ValueError):
            cache.incr_version("does_not_exist")

        cache.set("null", None)
        self.assertEqual(cache.incr_version("null"), 2)

    def test_decr_version(self):
        cache.set("answer", 42, version=2)
        self.assertIsNone(cache.get("answer"))
        self.assertIsNone(cache.get("answer", version=1))
        self.assertEqual(cache.get("answer", version=2), 42)

        self.assertEqual(cache.decr_version("answer", version=2), 1)
        self.assertEqual(cache.get("answer"), 42)
        self.assertEqual(cache.get("answer", version=1), 42)
        self.assertIsNone(cache.get("answer", version=2))

        caches["v2"].set("answer2", 42)
        self.assertEqual(caches["v2"].get("answer2"), 42)
        self.assertIsNone(caches["v2"].get("answer2", version=1))
        self.assertEqual(caches["v2"].get("answer2", version=2), 42)

        self.assertEqual(caches["v2"].decr_version("answer2"), 1)
        self.assertIsNone(caches["v2"].get("answer2"))
        self.assertEqual(caches["v2"].get("answer2", version=1), 42)
        self.assertIsNone(caches["v2"].get("answer2", version=2))

        with self.assertRaises(ValueError):
            cache.decr_version("does_not_exist", version=2)

        cache.set("null", None, version=2)
        self.assertEqual(cache.decr_version("null", version=2), 1)

    def test_custom_key_func(self):
        # Two caches with different key functions aren't visible to each other
        cache.set("answer1", 42)
        self.assertEqual(cache.get("answer1"), 42)
        self.assertIsNone(caches["custom_key"].get("answer1"))
        self.assertIsNone(caches["custom_key2"].get("answer1"))

        caches["custom_key"].set("answer2", 42)
        self.assertIsNone(cache.get("answer2"))
        self.assertEqual(caches["custom_key"].get("answer2"), 42)
        self.assertEqual(caches["custom_key2"].get("answer2"), 42)

    @override_settings(CACHE_MIDDLEWARE_ALIAS=DEFAULT_CACHE_ALIAS)
    def test_cache_write_unpicklable_object(self):
        fetch_middleware = FetchFromCacheMiddleware(empty_response)

        request = self.factory.get("/cache/test")
        request._cache_update_cache = True
        get_cache_data = FetchFromCacheMiddleware(empty_response).process_request(request)
        self.assertIsNone(get_cache_data)

        content = "Testing cookie serialization."

        def get_response(req):  # noqa: ARG001
            response = HttpResponse(content)
            response.set_cookie("foo", "bar")
            return response

        update_middleware = UpdateCacheMiddleware(get_response)
        response = update_middleware(request)

        get_cache_data = fetch_middleware.process_request(request)
        self.assertIsNotNone(get_cache_data)
        self.assertEqual(get_cache_data.content, content.encode())
        self.assertEqual(get_cache_data.cookies, response.cookies)

        UpdateCacheMiddleware(lambda req: get_cache_data)(request)  # noqa: ARG005
        get_cache_data = fetch_middleware.process_request(request)
        self.assertIsNotNone(get_cache_data)
        self.assertEqual(get_cache_data.content, content.encode())
        self.assertEqual(get_cache_data.cookies, response.cookies)

    def test_add_fail_on_pickleerror(self):
        # Shouldn't fail silently if trying to cache an unpicklable type.
        with self.assertRaises(pickle.PickleError):
            cache.add("unpicklable", Unpicklable())

    def test_set_fail_on_pickleerror(self):
        with self.assertRaises(pickle.PickleError):
            cache.set("unpicklable", Unpicklable())

    def test_get_or_set(self):
        self.assertIsNone(cache.get("projector"))
        self.assertEqual(cache.get_or_set("projector", 42), 42)
        self.assertEqual(cache.get("projector"), 42)
        self.assertIsNone(cache.get_or_set("null", None))
        # Previous get_or_set() stores None in the cache.
        self.assertIsNone(cache.get("null", "default"))

    def test_get_or_set_callable(self):
        def my_callable():
            return "value"

        self.assertEqual(cache.get_or_set("mykey", my_callable), "value")
        self.assertEqual(cache.get_or_set("mykey", my_callable()), "value")

        self.assertIsNone(cache.get_or_set("null", lambda: None))
        # Previous get_or_set() stores None in the cache.
        self.assertIsNone(cache.get("null", "default"))

    def test_get_or_set_version(self):
        msg = "get_or_set() missing 1 required positional argument: 'default'"
        self.assertEqual(cache.get_or_set("brian", 1979, version=2), 1979)
        with self.assertRaisesMessage(TypeError, msg):
            cache.get_or_set("brian")
        with self.assertRaisesMessage(TypeError, msg):
            cache.get_or_set("brian", version=1)
        self.assertIsNone(cache.get("brian", version=1))
        self.assertEqual(cache.get_or_set("brian", 42, version=1), 42)
        self.assertEqual(cache.get_or_set("brian", 1979, version=2), 1979)
        self.assertIsNone(cache.get("brian", version=3))

    def test_get_or_set_racing(self):
        with mock.patch(f"{settings.CACHES['default']['BACKEND']}.add") as cache_add:
            # Simulate cache.add() failing to add a value. In that case, the
            # default value should be returned.
            cache_add.return_value = False
            self.assertEqual(cache.get_or_set("key", "default"), "default")

    def test_collection_has_indexes(self):
        indexes = list(cache.collection_for_read.list_indexes())
        self.assertTrue(
            any(
                index["key"] == SON([("expires_at", 1)]) and index.get("expireAfterSeconds") == 0
                for index in indexes
            )
        )
        self.assertTrue(
            any(
                index["key"] == SON([("key", 1)]) and index.get("unique") is True
                for index in indexes
            )
        )

    def test_serializer_dumps(self):
        self.assertEqual(cache.serializer.dumps(123), 123)
        self.assertIsInstance(cache.serializer.dumps(True), bytes)
        self.assertIsInstance(cache.serializer.dumps("abc"), bytes)


class DBCacheRouter:
    """A router that puts the cache table on the 'other' database."""

    def db_for_read(self, model, **hints):
        if model._meta.app_label == "django_cache":
            return "other"
        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label == "django_cache":
            return "other"
        return None

    def allow_migrate(self, db, app_label, **hints):
        if app_label == "django_cache":
            return db == "other"
        return None


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django_mongodb_backend.cache.MongoDBCache",
            "LOCATION": "my_cache_table",
        },
    },
)
@modify_settings(
    INSTALLED_APPS={"prepend": "django_mongodb_backend"},
)
class CreateCacheCollectionTests(TestCase):
    databases = {"default", "other"}

    @override_settings(DATABASE_ROUTERS=[DBCacheRouter()])
    def test_createcachetable_observes_database_router(self):
        # cache table should not be created on 'default'
        with self.assertNumQueries(0, using="default"):
            management.call_command("createcachecollection", database="default", verbosity=0)
        # cache table should be created on 'other'
        # Queries:
        #   1: Create indexes
        with self.assertNumQueries(1, using="other"):
            management.call_command("createcachecollection", database="other", verbosity=0)
