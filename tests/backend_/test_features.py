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


class SupportsQueryableEncryptionTests(TestCase):
    def setUp(self):
        # Clear the cached property.
        connection.features.__dict__.pop("supports_queryable_encryption", None)
        # Must initialize the feature before patching it.
        connection.features._supports_transactions  # noqa: B018

    def tearDown(self):
        del connection.features.supports_queryable_encryption

    @staticmethod
    def enterprise_response(command):
        if command == "buildInfo":
            return {"modules": ["enterprise"]}
        raise Exception("Unexpected command")

    @staticmethod
    def non_enterprise_response(command):
        if command == "buildInfo":
            return {"modules": []}
        raise Exception("Unexpected command")

    def test_supported_on_atlas(self):
        """Supported on MongoDB 7.0+ Atlas replica set or sharded cluster."""
        with (
            patch(
                "pymongo.synchronous.database.Database.command", wraps=self.non_enterprise_response
            ),
            patch("django.db.connection.features.supports_atlas_search", True),
            patch("django.db.connection.features._supports_transactions", True),
            patch("django.db.connection.features.is_mongodb_7_0", True),
        ):
            self.assertIs(connection.features.supports_queryable_encryption, True)

    def test_supported_on_enterprise(self):
        """Supported on MongoDB 7.0+ Enterprise replica set or sharded cluster."""
        with (
            patch("pymongo.synchronous.database.Database.command", wraps=self.enterprise_response),
            patch("django.db.connection.features.supports_atlas_search", False),
            patch("django.db.connection.features._supports_transactions", True),
            patch("django.db.connection.features.is_mongodb_7_0", True),
        ):
            self.assertIs(connection.features.supports_queryable_encryption, True)

    def test_atlas_or_enterprise_required(self):
        """Not supported on MongoDB Community Edition."""
        with (
            patch(
                "pymongo.synchronous.database.Database.command", wraps=self.non_enterprise_response
            ),
            patch("django.db.connection.features.supports_atlas_search", False),
            patch("django.db.connection.features._supports_transactions", True),
            patch("django.db.connection.features.is_mongodb_7_0", True),
        ):
            self.assertIs(connection.features.supports_queryable_encryption, False)

    def test_transactions_required(self):
        """
        Not supported if database isn't a replica set or sharded cluster
        (i.e. DatabaseFeatures._supports_transactions = False).
        """
        with (
            patch("pymongo.synchronous.database.Database.command", wraps=self.enterprise_response),
            patch("django.db.connection.features.supports_atlas_search", False),
            patch("django.db.connection.features._supports_transactions", False),
            patch("django.db.connection.features.is_mongodb_7_0", True),
        ):
            self.assertIs(connection.features.supports_queryable_encryption, False)

    def test_mongodb_7_0_required(self):
        """Not supported on MongoDB < 7.0"""
        with (
            patch("pymongo.synchronous.database.Database.command", wraps=self.enterprise_response),
            patch("django.db.connection.features.supports_atlas_search", False),
            patch("django.db.connection.features._supports_transactions", True),
            patch("django.db.connection.features.is_mongodb_7_0", False),
        ):
            self.assertIs(connection.features.supports_queryable_encryption, False)
