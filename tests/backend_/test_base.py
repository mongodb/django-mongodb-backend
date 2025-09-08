from unittest.mock import patch

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
            DatabaseWrapper(settings)

    def test_database_name_empty_and_host_does_not_contain_database(self):
        settings = connection.settings_dict.copy()
        settings["NAME"] = ""
        settings["HOST"] = "mongodb://localhost"
        msg = 'settings.DATABASES is missing the "NAME" value.'
        with self.assertRaisesMessage(ImproperlyConfigured, msg):
            DatabaseWrapper(settings)

    def test_database_name_parsed_from_host(self):
        settings = connection.settings_dict.copy()
        settings["NAME"] = ""
        settings["HOST"] = "mongodb://localhost/db"
        self.assertEqual(DatabaseWrapper(settings).settings_dict["NAME"], "db")

    def test_database_name_parsed_from_srv_host(self):
        settings = connection.settings_dict.copy()
        settings["NAME"] = ""
        settings["HOST"] = "mongodb+srv://localhost/db"
        # patch() prevents a crash when PyMongo attempts to resolve the
        # nonexistent SRV record.
        with patch("dns.resolver.resolve"):
            self.assertEqual(DatabaseWrapper(settings).settings_dict["NAME"], "db")

    def test_database_name_not_overridden_by_host(self):
        settings = connection.settings_dict.copy()
        settings["NAME"] = "not overridden"
        settings["HOST"] = "mongodb://localhost/db"
        self.assertEqual(DatabaseWrapper(settings).settings_dict["NAME"], "not overridden")


class GetConnectionParamsTests(SimpleTestCase):
    def test_host(self):
        settings = connection.settings_dict.copy()
        settings["HOST"] = "host"
        params = DatabaseWrapper(settings).get_connection_params()
        self.assertEqual(params["host"], "host")

    def test_host_empty(self):
        settings = connection.settings_dict.copy()
        settings["HOST"] = ""
        params = DatabaseWrapper(settings).get_connection_params()
        self.assertIsNone(params["host"])

    def test_user(self):
        settings = connection.settings_dict.copy()
        settings["USER"] = "user"
        params = DatabaseWrapper(settings).get_connection_params()
        self.assertEqual(params["username"], "user")

    def test_password(self):
        settings = connection.settings_dict.copy()
        settings["PASSWORD"] = "password"  # noqa: S105
        params = DatabaseWrapper(settings).get_connection_params()
        self.assertEqual(params["password"], "password")

    def test_port(self):
        settings = connection.settings_dict.copy()
        settings["PORT"] = 123
        params = DatabaseWrapper(settings).get_connection_params()
        self.assertEqual(params["port"], 123)

    def test_port_as_string(self):
        settings = connection.settings_dict.copy()
        settings["PORT"] = "123"
        params = DatabaseWrapper(settings).get_connection_params()
        self.assertEqual(params["port"], 123)

    def test_options(self):
        settings = connection.settings_dict.copy()
        settings["OPTIONS"] = {"extra": "option"}
        params = DatabaseWrapper(settings).get_connection_params()
        self.assertEqual(params["extra"], "option")

    def test_unspecified_settings_omitted(self):
        settings = connection.settings_dict.copy()
        # django.db.utils.ConnectionHandler sets unspecified values to an empty
        # string.
        settings.update(
            {
                "USER": "",
                "PASSWORD": "",
                "PORT": "",
            }
        )
        params = DatabaseWrapper(settings).get_connection_params()
        self.assertNotIn("username", params)
        self.assertNotIn("password", params)
        self.assertNotIn("port", params)


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
