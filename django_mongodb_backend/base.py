import contextlib
import os

from django.core.exceptions import ImproperlyConfigured
from django.db.backends.base.base import BaseDatabaseWrapper
from django.utils.asyncio import async_unsafe
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


class DatabaseWrapper(BaseDatabaseWrapper):
    data_types = {
        "AutoField": "int",
        "BigAutoField": "long",
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
        "IntegerField": "int",
        "BigIntegerField": "long",
        "GenericIPAddressField": "string",
        "JSONField": "object",
        "OneToOneField": "int",
        "PositiveBigIntegerField": "int",
        "PositiveIntegerField": "long",
        "PositiveSmallIntegerField": "int",
        "SlugField": "string",
        "SmallAutoField": "int",
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
        "lt": lambda a, b: {"$and": [{"$lt": [a, b]}, {"$ne": [a, None]}]},
        "lte": lambda a, b: {"$and": [{"$lte": [a, b]}, {"$ne": [a, None]}]},
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

    def get_collection(self, name, **kwargs):
        collection = Collection(self.database, name, **kwargs)
        if self.queries_logged:
            collection = OperationDebugWrapper(self, collection)
        return collection

    def get_database(self):
        if self.queries_logged:
            return OperationDebugWrapper(self)
        return self.database

    def __getattr__(self, attr):
        """Connect to the database the first time `database` is accessed."""
        if attr == "database":
            if self.connection is None:
                self.connect()
            return getattr(self, attr)
        raise AttributeError(attr)

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
        return MongoClient(**conn_params, driver=self._driver_info())

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

    @async_unsafe
    def close(self):
        super().close()
        with contextlib.suppress(AttributeError):
            del self.database

    @async_unsafe
    def cursor(self):
        return Cursor()

    def get_database_version(self):
        """Return a tuple of the database's version."""
        return tuple(self.connection.server_info()["versionArray"])
