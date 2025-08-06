import contextlib
import logging
import os

from django.core.exceptions import ImproperlyConfigured
from django.db import DEFAULT_DB_ALIAS
from django.db.backends.base.base import BaseDatabaseWrapper
from django.db.backends.utils import debug_transaction
from django.utils.asyncio import async_unsafe
from django.utils.functional import cached_property
from pymongo.collection import Collection
from pymongo.driver_info import DriverInfo
from pymongo.mongo_client import MongoClient

from . import __version__ as django_mongodb_backend_version
from . import dbapi as Database
from .client import DatabaseClient
from .creation import DatabaseCreation
from .features import DatabaseFeatures
from .introspection import DatabaseIntrospection
from .operations import DatabaseOperations
from .query_utils import regex_match
from .schema import DatabaseSchemaEditor
from .utils import OperationDebugWrapper
from .validation import DatabaseValidation


class Cursor:
    """A "nodb" cursor that does nothing except work on a context manager."""

    def __enter__(self):
        pass

    def __exit__(self, exception_type, exception_value, exception_traceback):
        pass


logger = logging.getLogger("django.db.backends.base")


class DatabaseWrapper(BaseDatabaseWrapper):
    data_types = {
        "AutoField": "",  # Not supported
        "BigAutoField": "",  # Not supported
        "BinaryField": "binData",
        "BooleanField": "bool",
        "CharField": "string",
        "DateField": "date",
        "DateTimeField": "date",
        "DecimalField": "decimal",
        "DurationField": "long",
        "FileField": "string",
        "FilePathField": "string",
        "FloatField": "double",
        "IntegerField": "long",
        "BigIntegerField": "long",
        "GenericIPAddressField": "string",
        "JSONField": "object",
        "PositiveBigIntegerField": "long",
        "PositiveIntegerField": "long",
        "PositiveSmallIntegerField": "int",
        "SlugField": "string",
        "SmallAutoField": "",  # Not supported
        "SmallIntegerField": "int",
        "TextField": "string",
        "TimeField": "date",
        "UUIDField": "string",
    }
    # Django uses these operators to generate SQL queries before it generates
    # MQL queries.
    operators = {
        "exact": "= %s",
        "iexact": "= UPPER(%s)",
        "contains": "LIKE %s",
        "icontains": "LIKE UPPER(%s)",
        "regex": "~ %s",
        "iregex": "~* %s",
        "gt": "> %s",
        "gte": ">= %s",
        "lt": "< %s",
        "lte": "<= %s",
        "startswith": "LIKE %s",
        "endswith": "LIKE %s",
        "istartswith": "LIKE UPPER(%s)",
        "iendswith": "LIKE UPPER(%s)",
    }
    # As with `operators`, these patterns are used to generate SQL before MQL.
    pattern_esc = "%%"
    pattern_ops = {
        "contains": "LIKE '%%' || {} || '%%'",
        "icontains": "LIKE '%%' || UPPER({}) || '%%'",
        "startswith": "LIKE {} || '%%'",
        "istartswith": "LIKE UPPER({}) || '%%'",
        "endswith": "LIKE '%%' || {}",
        "iendswith": "LIKE '%%' || UPPER({})",
    }
    _connection_pools = {}

    def _isnull_operator(a, b):
        is_null = {
            "$or": [
                # The path does not exist (i.e. is "missing")
                {"$eq": [{"$type": a}, "missing"]},
                # or the value is None.
                {"$eq": [a, None]},
            ]
        }
        return is_null if b else {"$not": is_null}

    mongo_operators = {
        "exact": lambda a, b: {"$eq": [a, b]},
        "gt": lambda a, b: {"$gt": [a, b]},
        "gte": lambda a, b: {"$gte": [a, b]},
        # MongoDB considers null less than zero. Exclude null values to match
        # SQL behavior.
        "lt": lambda a, b: {"$and": [{"$lt": [a, b]}, DatabaseWrapper._isnull_operator(a, False)]},
        "lte": lambda a, b: {
            "$and": [{"$lte": [a, b]}, DatabaseWrapper._isnull_operator(a, False)]
        },
        "in": lambda a, b: {"$in": [a, b]},
        "isnull": _isnull_operator,
        "range": lambda a, b: {
            "$and": [
                {"$or": [DatabaseWrapper._isnull_operator(b[0], True), {"$gte": [a, b[0]]}]},
                {"$or": [DatabaseWrapper._isnull_operator(b[1], True), {"$lte": [a, b[1]]}]},
            ]
        },
        "iexact": lambda a, b: regex_match(a, ("^", b, {"$literal": "$"}), insensitive=True),
        "startswith": lambda a, b: regex_match(a, ("^", b)),
        "istartswith": lambda a, b: regex_match(a, ("^", b), insensitive=True),
        "endswith": lambda a, b: regex_match(a, (b, {"$literal": "$"})),
        "iendswith": lambda a, b: regex_match(a, (b, {"$literal": "$"}), insensitive=True),
        "contains": lambda a, b: regex_match(a, b),
        "icontains": lambda a, b: regex_match(a, b, insensitive=True),
        "regex": lambda a, b: regex_match(a, b),
        "iregex": lambda a, b: regex_match(a, b, insensitive=True),
    }

    display_name = "MongoDB"
    vendor = "mongodb"
    Database = Database
    SchemaEditorClass = DatabaseSchemaEditor
    client_class = DatabaseClient
    creation_class = DatabaseCreation
    features_class = DatabaseFeatures
    introspection_class = DatabaseIntrospection
    ops_class = DatabaseOperations
    validation_class = DatabaseValidation

    def __init__(self, settings_dict, alias=DEFAULT_DB_ALIAS):
        super().__init__(settings_dict, alias=alias)
        self.session = None
        # Tracks whether the connection is in a transaction managed by
        # django_mongodb_backend.transaction.atomic. `in_atomic_block` isn't
        # used in case Django's atomic() (used internally in Django) is called
        # within this package's atomic().
        self.in_atomic_block_mongo = False
        # Current number of nested 'atomic' calls.
        self.nested_atomics = 0

    def get_collection(self, name, **kwargs):
        collection = Collection(self.database, name, **kwargs)
        if self.queries_logged:
            collection = OperationDebugWrapper(self, collection)
        return collection

    def get_database(self):
        if self.queries_logged:
            return OperationDebugWrapper(self)
        return self.database

    @cached_property
    def database(self):
        """Connect to the database the first time it's accessed."""
        if self.connection is None:
            self.connect()
        # Cache the database attribute set by init_connection_state()
        return self.database

    def init_connection_state(self):
        self.database = self.connection[self.settings_dict["NAME"]]
        super().init_connection_state()

    def get_connection_params(self):
        settings_dict = self.settings_dict
        if not settings_dict["NAME"]:
            raise ImproperlyConfigured('settings.DATABASES is missing the "NAME" value.')
        return {
            "host": settings_dict["HOST"] or None,
            "port": int(settings_dict["PORT"] or 27017),
            "username": settings_dict.get("USER"),
            "password": settings_dict.get("PASSWORD"),
            **settings_dict["OPTIONS"],
        }

    @async_unsafe
    def get_new_connection(self, conn_params):
        if self.alias not in self._connection_pools:
            conn = MongoClient(**conn_params, driver=self._driver_info())
            # setdefault() ensures that multiple threads don't set this in
            # parallel.
            self._connection_pools.setdefault(self.alias, conn)
        return self._connection_pools[self.alias]

    def _driver_info(self):
        if not os.environ.get("RUNNING_DJANGOS_TEST_SUITE"):
            return DriverInfo("django-mongodb-backend", django_mongodb_backend_version)
        return None

    def _commit(self):
        pass

    def _rollback(self):
        pass

    def set_autocommit(self, autocommit, force_begin_transaction_with_broken_autocommit=False):
        self.autocommit = autocommit

    def _close(self):
        # Normally called by close(), this method is also called by some tests.
        pass

    @async_unsafe
    def close(self):
        self.validate_thread_sharing()
        # MongoClient is a connection pool and, unlike database drivers that
        # implement PEP 249, shouldn't be closed by connection.close().

    def close_pool(self):
        """Close the MongoClient."""
        # Clear commit hooks and session.
        self.run_on_commit = []
        if self.session:
            self._end_session()
        connection = self.connection
        if connection is None:
            return
        # Remove all references to the connection.
        self.connection = None
        with contextlib.suppress(AttributeError):
            del self.database
        del self._connection_pools[self.alias]
        # Then close it.
        connection.close()

    @async_unsafe
    def cursor(self):
        return Cursor()

    def get_database_version(self):
        """Return a tuple of the database's version."""
        return tuple(self.connection.server_info()["versionArray"])

    ## Transaction API for django_mongodb_backend.transaction.atomic()
    @async_unsafe
    def start_transaction_mongo(self):
        if self.session is None:
            self.session = self.connection.start_session()
            with debug_transaction(self, "session.start_transaction()"):
                self.session.start_transaction()

    @async_unsafe
    def commit_mongo(self):
        if self.session:
            with debug_transaction(self, "session.commit_transaction()"):
                self.session.commit_transaction()
            self._end_session()
        self.run_and_clear_commit_hooks()

    @async_unsafe
    def rollback_mongo(self):
        if self.session:
            with debug_transaction(self, "session.abort_transaction()"):
                self.session.abort_transaction()
            self._end_session()
        self.run_on_commit = []

    def _end_session(self):
        self.session.end_session()
        self.session = None

    def on_commit(self, func, robust=False):
        """
        Copied from BaseDatabaseWrapper.on_commit() except that it checks
        in_atomic_block_mongo instead of in_atomic_block.
        """
        if not callable(func):
            raise TypeError("on_commit()'s callback must be a callable.")
        if self.in_atomic_block_mongo:
            # Transaction in progress; save for execution on commit.
            # The first item in the tuple (an empty list) is normally the
            # savepoint IDs, which isn't applicable on MongoDB.
            self.run_on_commit.append(([], func, robust))
        else:
            # No transaction in progress; execute immediately.
            if robust:
                try:
                    func()
                except Exception as e:
                    logger.exception(
                        "Error calling %s in on_commit() (%s).",
                        func.__qualname__,
                        e,
                    )
            else:
                func()
