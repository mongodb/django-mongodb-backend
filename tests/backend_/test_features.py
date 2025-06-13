from unittest.mock import patch

from django.db import connection
from django.test import TestCase


class SupportsTransactionsTests(TestCase):
    def setUp(self):
        # Clear the cached property.
        del connection.features.supports_transactions

    def tearDown(self):
        del connection.features.supports_transactions

    def test_replica_set(self):
        """A replica set supports transactions."""

        def mocked_command(command):
            if command == "hello":
                return {"setName": "foo"}
            if command == "serverStatus":
                return {"storageEngine": {"name": "wiredTiger"}}
            raise Exception("Unexpected command")

        with patch("pymongo.synchronous.database.Database.command", wraps=mocked_command):
            self.assertIs(connection.features.supports_transactions, True)

    def test_replica_set_other_storage_engine(self):
        """No support on a non-wiredTiger replica set."""

        def mocked_command(command):
            if command == "hello":
                return {"setName": "foo"}
            if command == "serverStatus":
                return {"storageEngine": {"name": "other"}}
            raise Exception("Unexpected command")

        with patch("pymongo.synchronous.database.Database.command", wraps=mocked_command):
            self.assertIs(connection.features.supports_transactions, False)

    def test_sharded_cluster(self):
        """A sharded cluster with wiredTiger storage engine supports them."""

        def mocked_command(command):
            if command == "hello":
                return {"msg": "isdbgrid"}
            if command == "serverStatus":
                return {"storageEngine": {"name": "wiredTiger"}}
            raise Exception("Unexpected command")

        with patch("pymongo.synchronous.database.Database.command", wraps=mocked_command):
            self.assertIs(connection.features.supports_transactions, True)

    def test_sharded_cluster_other_storage_engine(self):
        """No support on a non-wiredTiger shared cluster."""

        def mocked_command(command):
            if command == "hello":
                return {"msg": "isdbgrid"}
            if command == "serverStatus":
                return {"storageEngine": {"name": "other"}}
            raise Exception("Unexpected command")

        with patch("pymongo.synchronous.database.Database.command", wraps=mocked_command):
            self.assertIs(connection.features.supports_transactions, False)

    def test_no_support(self):
        """No support on a non-replica set, non-sharded cluster."""

        def mocked_command(command):
            if command == "hello":
                return {}
            raise Exception("Unexpected command")

        with patch("pymongo.synchronous.database.Database.command", wraps=mocked_command):
            self.assertIs(connection.features.supports_transactions, False)
