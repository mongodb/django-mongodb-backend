from unittest.mock import patch

from django.db import connection
from django.test import TestCase


class SupportsTransactionsTests(TestCase):
    def setUp(self):
        # Clear the cached property.
        connection.features.__dict__.pop("_supports_transactions", None)

    def tearDown(self):
        del connection.features._supports_transactions

    def test_replica_set(self):
        """A replica set supports transactions."""

        def mocked_command(command):
            if command == "hello":
                return {"setName": "foo"}
            raise Exception("Unexpected command")

        with patch("pymongo.synchronous.database.Database.command", wraps=mocked_command):
            self.assertIs(connection.features._supports_transactions, True)

    def test_sharded_cluster(self):
        """A sharded cluster supports transactions."""

        def mocked_command(command):
            if command == "hello":
                return {"msg": "isdbgrid"}
            raise Exception("Unexpected command")

        with patch("pymongo.synchronous.database.Database.command", wraps=mocked_command):
            self.assertIs(connection.features._supports_transactions, True)

    def test_no_support(self):
        """No support on a non-replica set, non-sharded cluster."""

        def mocked_command(command):
            if command == "hello":
                return {}
            raise Exception("Unexpected command")

        with patch("pymongo.synchronous.database.Database.command", wraps=mocked_command):
            self.assertIs(connection.features._supports_transactions, False)
