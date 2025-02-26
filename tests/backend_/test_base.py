from django.core.exceptions import ImproperlyConfigured
from django.db import connection
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
