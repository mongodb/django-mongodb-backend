import contextlib
import logging
import os

from bson import Decimal128
from django.core.exceptions import EmptyResultSet, FullResultSet, ImproperlyConfigured
from django.db import DEFAULT_DB_ALIAS
from django.db.backends.base.base import BaseDatabaseWrapper
from django.db.backends.utils import debug_transaction
from django.utils.asyncio import async_unsafe
from django.utils.functional import cached_property
from pymongo.collection import Collection
from pymongo.driver_info import DriverInfo
from pymongo.encryption import ClientEncryption
from pymongo.mongo_client import MongoClient
from pymongo.uri_parser import parse_uri

from . import __version__ as django_mongodb_backend_version
from . import dbapi as Database
from .client import DatabaseClient
from .creation import DatabaseCreation
from .features import DatabaseFeatures
from .introspection import DatabaseIntrospection
from .operations import DatabaseOperations
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

    def _isnull_operator(field, is_null):
        if is_null:
            return {"$or": [{field: {"$exists": False}}, {field: None}]}
        return {"$and": [{field: {"$exists": True}}, {field: {"$ne": None}}]}

    def _range_operator(a, b):
        conditions = []
        start, end = b
        if start is not None:
            conditions.append({a: {"$gte": b[0]}})
        if end is not None:
            conditions.append({a: {"$lte": b[1]}})
        if not conditions:
            raise FullResultSet
        if start is not None and end is not None:
            # Decimal128 can't be natively compared.
            if isinstance(start, Decimal128):
                start = start.to_decimal()
            if isinstance(end, Decimal128):
                end = end.to_decimal()
            if start > end:
                raise EmptyResultSet
        return {"$and": conditions}

    def _regex_operator(field, regex, insensitive=False):
        options = "i" if insensitive else ""
        return {field: {"$regex": regex, "$options": options}}

    mongo_operators = {
        "exact": lambda a, b: {a: b},
        "gt": lambda a, b: {a: {"$gt": b}},
        "gte": lambda a, b: {a: {"$gte": b}},
        # MongoDB considers null less than zero. Exclude null values to match
        # SQL behavior.
        "lt": lambda a, b: {"$and": [{a: {"$lt": b}}, DatabaseWrapper._isnull_operator(a, False)]},
        "lte": lambda a, b: {
            "$and": [{a: {"$lte": b}}, DatabaseWrapper._isnull_operator(a, False)]
        },
        "in": lambda a, b: {a: {"$in": tuple(b)}},
        "isnull": _isnull_operator,
        "range": _range_operator,
        "iexact": lambda a, b: DatabaseWrapper._regex_operator(a, f"^{b}$", insensitive=True),
        "startswith": lambda a, b: DatabaseWrapper._regex_operator(a, f"^{b}"),
        "istartswith": lambda a, b: DatabaseWrapper._regex_operator(a, f"^{b}", insensitive=True),
        "endswith": lambda a, b: DatabaseWrapper._regex_operator(a, f"{b}$"),
        "iendswith": lambda a, b: DatabaseWrapper._regex_operator(a, f"{b}$", insensitive=True),
        "contains": lambda a, b: DatabaseWrapper._regex_operator(a, b),
        "icontains": lambda a, b: DatabaseWrapper._regex_operator(a, b, insensitive=True),
        "regex": lambda a, b: DatabaseWrapper._regex_operator(a, b),
        "iregex": lambda a, b: DatabaseWrapper._regex_operator(a, b, insensitive=True),
    }

    def _isnull_expr(field, is_null):
        mql = {
            "$or": [
                # The path does not exist (i.e. is "missing")
                {"$eq": [{"$type": field}, "missing"]},
                # or the value is None.
                {"$eq": [field, None]},
            ]
        }
        return mql if is_null else {"$not": mql}

    def _regex_expr(field, regex_vals, insensitive=False):
        regex = {"$concat": regex_vals} if isinstance(regex_vals, tuple) else regex_vals
        options = "i" if insensitive else ""
        return {"$regexMatch": {"input": field, "regex": regex, "options": options}}

    mongo_expr_operators = {
        "exact": lambda a, b: {"$eq": [a, b]},
        "gt": lambda a, b: {"$gt": [a, b]},
        "gte": lambda a, b: {"$gte": [a, b]},
        # MongoDB considers null less than zero. Exclude null values to match
        # SQL behavior.
        "lt": lambda a, b: {"$and": [{"$lt": [a, b]}, DatabaseWrapper._isnull_expr(a, False)]},
        "lte": lambda a, b: {"$and": [{"$lte": [a, b]}, DatabaseWrapper._isnull_expr(a, False)]},
        "in": lambda a, b: {"$in": [a, b]},
        "isnull": _isnull_expr,
        "range": lambda a, b: {
            "$and": [
                {"$or": [DatabaseWrapper._isnull_expr(b[0], True), {"$gte": [a, b[0]]}]},
                {"$or": [DatabaseWrapper._isnull_expr(b[1], True), {"$lte": [a, b[1]]}]},
            ]
        },
        "iexact": lambda a, b: DatabaseWrapper._regex_expr(
            a, ("^", b, {"$literal": "$"}), insensitive=True
        ),
        "startswith": lambda a, b: DatabaseWrapper._regex_expr(a, ("^", b)),
        "istartswith": lambda a, b: DatabaseWrapper._regex_expr(a, ("^", b), insensitive=True),
        "endswith": lambda a, b: DatabaseWrapper._regex_expr(a, (b, {"$literal": "$"})),
        "iendswith": lambda a, b: DatabaseWrapper._regex_expr(
            a, (b, {"$literal": "$"}), insensitive=True
        ),
        "contains": lambda a, b: DatabaseWrapper._regex_expr(a, b),
        "icontains": lambda a, b: DatabaseWrapper._regex_expr(a, b, insensitive=True),
        "regex": lambda a, b: DatabaseWrapper._regex_expr(a, b),
        "iregex": lambda a, b: DatabaseWrapper._regex_expr(a, b, insensitive=True),
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
        # If database "NAME" isn't specified, try to get it from HOST, if it's
        # a connection string.
        if self.settings_dict["NAME"] == "":  # Empty string = unspecified; None = _nodb_cursor()
            name_is_missing = True
            host = self.settings_dict["HOST"]
            if host.startswith(("mongodb://", "mongodb+srv://")):
                uri = parse_uri(host)
                if database := uri.get("database"):
                    self.settings_dict["NAME"] = database
                    name_is_missing = False
            if name_is_missing:
                raise ImproperlyConfigured('settings.DATABASES is missing the "NAME" value.')

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
        params = {
            "host": settings_dict["HOST"] or None,
            **settings_dict["OPTIONS"],
        }
        # MongoClient uses any of these parameters (including "OPTIONS" above)
        # to override any corresponding values in a connection string "HOST".
        if user := settings_dict.get("USER"):
            params["username"] = user
        if password := settings_dict.get("PASSWORD"):
            params["password"] = password
        if port := settings_dict.get("PORT"):
            params["port"] = int(port)
        return params

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
            self.ensure_connection()
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

    ## Queryable Encryption properties
    @cached_property
    def auto_encryption_opts(self):
        return self.connection._options.auto_encryption_opts

    @cached_property
    def client_encryption(self):
        if auto_encryption_opts := self.auto_encryption_opts:
            return ClientEncryption(
                auto_encryption_opts._kms_providers,
                auto_encryption_opts._key_vault_namespace,
                self.connection,
                self.connection.codec_options,
            )
        return None

    @cached_property
    def key_vault(self):
        # The key vault collection.
        _, key_vault_collection = self.auto_encryption_opts._key_vault_namespace.split(".", 1)
        return self.get_collection(key_vault_collection)

    @cached_property
    def kms_provider(self):
        # The KMS provider.
        kms_providers = self.auto_encryption_opts._kms_providers
        if len(kms_providers) == 1:
            return next(iter(kms_providers.keys()))
        # Multiple providers are configured since AutoEncryptionOpts requires
        # at least one.
        raise ImproperlyConfigured(
            "Multiple KMS providers per database aren't supported. Please "
            "create a feature request with details about your use case."
        )

    @cached_property
    def kms_credentials(self):
        # The KMS credentials (also called "master key"). N/A for local KMS.
        kms_provider = self.kms_provider
        if kms_provider == "local":
            return None
        if "KMS_CREDENTIALS" not in self.settings_dict:
            raise ImproperlyConfigured(
                f"DATABASES['{self.alias}'] is missing 'KMS_CREDENTIALS' "
                f"required for KMS '{kms_provider}'."
            )
        if kms_provider not in self.settings_dict["KMS_CREDENTIALS"]:
            raise ImproperlyConfigured(
                f"DATABASES['{self.alias}']['KMS_CREDENTIALS'] is missing '{kms_provider}' key."
            )
        return self.settings_dict["KMS_CREDENTIALS"][kms_provider]
