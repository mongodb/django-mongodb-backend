from django.conf import settings
from django.db.backends.base.creation import TEST_DATABASE_PREFIX, BaseDatabaseCreation


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
