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
                # Importing a test app that isn't installed raises RuntimeError.
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
