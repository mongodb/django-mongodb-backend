from django.core.exceptions import ImproperlyConfigured
from django.db import connection
from django.db.backends.signals import connection_created
from django.test import SimpleTestCase, TestCase

from django_mongodb_backend.base import DatabaseWrapper


class DatabaseWrapperTests(SimpleTestCase):
    def test_database_name_empty(self):
        settings = connection.settings_dict.copy()
        settings["NAME"] = ""
        msg = 'settings.DATABASES is missing the "NAME" value.'
        with self.assertRaisesMessage(ImproperlyConfigured, msg):
            DatabaseWrapper(settings).get_connection_params()


class DatabaseWrapperConnectionTests(TestCase):
    def test_set_autocommit(self):
        self.assertIs(connection.get_autocommit(), True)
        connection.set_autocommit(False)
        self.assertIs(connection.get_autocommit(), False)
        connection.set_autocommit(True)
        self.assertIs(connection.get_autocommit(), True)

    def test_close(self):
        """connection.close() doesn't close the connection."""
        conn = connection.connection
        self.assertIsNotNone(conn)
        connection.close()
        self.assertEqual(connection.connection, conn)

    def test_close_pool(self):
        """connection.close_pool() closes the connection."""
        self.assertIsNotNone(connection.connection)
        connection.close_pool()
        self.assertIsNone(connection.connection)

    def test_connection_created_database_attr(self):
        """
        connection.database is available in the connection_created signal.
        """
        data = {}

        def receiver(sender, connection, **kwargs):  # noqa: ARG001
            data["database"] = connection.database

        connection_created.connect(receiver)
        connection.close_pool()
        # Accessing database implicitly connects.
        connection.database  # noqa: B018
        self.assertIs(data["database"], connection.database)
        connection.close_pool()
        connection_created.disconnect(receiver)
        data.clear()
        connection.connect()
        self.assertEqual(data, {})
