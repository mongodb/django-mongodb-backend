from django.conf import settings
from django.core.cache import caches
from django.db.backends.base.creation import BaseDatabaseCreation

from django_mongodb_backend.cache import MongoDBCache


class DatabaseCreation(BaseDatabaseCreation):
    def _execute_create_test_db(self, cursor, parameters, keepdb=False):
        if not keepdb:
            self._destroy_test_db(parameters["dbname"], verbosity=0)

    def _destroy_test_db(self, test_database_name, verbosity):
        # At this point, settings still points to the non-test database. For
        # MongoDB, it must use the test database.
        settings.DATABASES[self.connection.alias]["NAME"] = test_database_name
        self.connection.settings_dict["NAME"] = test_database_name

        for collection in self.connection.introspection.table_names():
            if not collection.startswith("system."):
                self.connection.database.drop_collection(collection)

    def create_test_db(self, *args, **kwargs):
        test_database_name = super().create_test_db(*args, **kwargs)
        # Create cache collections
        for cache_alias in settings.CACHES:
            cache = caches[cache_alias]
            if isinstance(cache, MongoDBCache):
                connection = cache._db_to_write
                if cache._collection_name in connection.introspection.table_names():
                    continue
                cache.create_indexes()
        return test_database_name
