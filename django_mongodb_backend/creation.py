import functools
import sys
import types

from django.conf import settings
from django.db.backends.base.creation import TEST_DATABASE_PREFIX, BaseDatabaseCreation
from django.utils.module_loading import import_string


def assertRaises(exception, message):
    """
    Wrap a test to assert that it raise the given exception with the given
    message.
    """

    def decorator(test):
        # Protect against a class reference in django_test_expected_raises.
        if not isinstance(test, types.FunctionType):
            raise TypeError(
                "Items in django_test_expected_raises must be test methods (got {test})."
            )

        @functools.wraps(test)
        def assert_raises_wrapper(self, *args, **kwargs):
            with self.assertRaisesMessage(exception, message):
                test(self, *args, **kwargs)

        return assert_raises_wrapper

    return decorator


class DatabaseCreation(BaseDatabaseCreation):
    def _execute_create_test_db(self, cursor, parameters, keepdb=False):
        # Close the connection (which may point to the non-test database) so
        # that a new connection to the test database can be established later.
        self.connection.close_pool()
        # Use a test _key_vault_namespace. This assumes the key vault database
        # is the same as the encrypted database so that _destroy_test_db() can
        # reset the collection by dropping it.
        if opts := self.connection.settings_dict["OPTIONS"].get("auto_encryption_opts"):
            self.connection.settings_dict["OPTIONS"][
                "auto_encryption_opts"
            ]._key_vault_namespace = TEST_DATABASE_PREFIX + opts._key_vault_namespace
        if not keepdb:
            self._destroy_test_db(parameters["dbname"], verbosity=0)

    def _clone_test_db(self, suffix, verbosity, keepdb=False):
        source_database_name = self.connection.settings_dict["NAME"]
        target_database_name = self.get_test_db_clone_settings(suffix)["NAME"]
        self.connection.ensure_connection()
        client = self.connection.connection
        if keepdb and target_database_name in client.list_database_names():
            return
        client.drop_database(target_database_name)
        source_db = client[source_database_name]
        target_db = client[target_database_name]
        for collection_name in source_db.list_collection_names():
            if collection_name.startswith("system."):
                continue
            source_collection = source_db[collection_name]
            # Copy documents to the target database.
            source_collection.aggregate(
                [{"$out": {"db": target_database_name, "coll": collection_name}}]
            )
            # Copy non-_id indexes ($out only creates the _id index).
            target_collection = target_db[collection_name]
            for index in source_collection.list_indexes():
                if index["name"] == "_id_":
                    continue
                keys = list(index["key"].items())
                options = {k: v for k, v in index.items() if k not in {"key", "v", "ns", "name"}}
                target_collection.create_index(keys, name=index["name"], **options)

    def _destroy_test_db(self, test_database_name, verbosity):
        # At this point, settings still points to the non-test database. For
        # MongoDB, it must use the test database.
        settings.DATABASES[self.connection.alias]["NAME"] = test_database_name
        self.connection.settings_dict["NAME"] = test_database_name

        for collection in self.connection.introspection.table_names():
            if not collection.startswith("system."):
                self.connection.database.drop_collection(collection)

    def destroy_test_db(self, old_database_name=None, verbosity=1, keepdb=False, suffix=None):
        super().destroy_test_db(old_database_name, verbosity, keepdb, suffix)
        # Close the connection to the test database.
        self.connection.close_pool()
        # Restore the original _key_vault_namespace.
        if opts := self.connection.settings_dict["OPTIONS"].get("auto_encryption_opts"):
            self.connection.settings_dict["OPTIONS"][
                "auto_encryption_opts"
            ]._key_vault_namespace = opts._key_vault_namespace[len(TEST_DATABASE_PREFIX) :]

    def setup_worker_connection(self, _worker_id):
        super().setup_worker_connection(_worker_id)
        # super() calls connection.close() which is a no-op for MongoDB.
        # Instead, the connection pool that points to the non-test database is
        # closed so that a connection to the test database can be established.
        # For encrypted databases, update the key vault namespace to the clone
        # database before reconnecting so the new MongoClient uses the correct
        # key vault.
        if opts := self.connection.settings_dict["OPTIONS"].get("auto_encryption_opts"):
            _, key_vault_collection = opts._key_vault_namespace.split(".", 1)
            opts._key_vault_namespace = (
                f"{self.connection.settings_dict['NAME']}.{key_vault_collection}"
            )
        self.connection.close_pool()

    def mark_expected_failures_and_skips(self):
        super().mark_expected_failures_and_skips()
        # Add an assertion wrapper to tests that are expected to raise an
        # exception (most often NotSupportedError).
        if self.connection.alias != "default":
            # Wrap tests only once since assertRaises() doesn't work if nested.
            return
        for (exception, msg), tests in self.connection.features.django_test_expected_raises.items():
            for test_name in tests:
                module_or_class_name, _, name_to_mark = test_name.rpartition(".")
                test_app = test_name.split(".")[0]
                # Importing an uninstalled test app raises RuntimeError.
                if test_app in settings.INSTALLED_APPS:
                    try:
                        test_frame = import_string(module_or_class_name)
                    except ImportError:
                        # Same comment from similar logic in superclass.
                        test_to_mark = import_string(test_name)
                        test_frame = sys.modules.get(test_to_mark.__module__)
                    else:
                        test_to_mark = getattr(test_frame, name_to_mark)
                    setattr(test_frame, name_to_mark, assertRaises(exception, msg)(test_to_mark))
