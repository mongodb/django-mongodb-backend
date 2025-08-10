import os
from io import StringIO

import pymongo
from bson import json_util
from django.core.management import call_command
from django.db import connections
from django.test import TransactionTestCase, modify_settings, override_settings
from pymongo.encryption import AutoEncryptionOpts

from .routers import TestEncryptedRouter


@modify_settings(
    INSTALLED_APPS={"prepend": "django_mongodb_backend"},
)
@override_settings(DATABASE_ROUTERS=[TestEncryptedRouter()])
class EncryptedFieldsManagementCommandTests(TransactionTestCase):
    databases = {"default", "encrypted"}
    available_apps = ["django_mongodb_backend", "encryption_"]
    expected_patient_record = {
        "fields": [
            {
                "bsonType": "string",
                "path": "ssn",
                "queries": {"queryType": "equality"},
            },
            {
                "bsonType": "date",
                "path": "birth_date",
                "queries": {"queryType": "range"},
            },
            {
                "bsonType": "binData",
                "path": "profile_picture",
                "queries": {"queryType": "equality"},
            },
            {
                "bsonType": "int",
                "path": "patient_age",
                "queries": {"queryType": "range", "max": 100, "min": 0},
            },
            {
                "bsonType": "double",
                "path": "weight",
                "queries": {"queryType": "range"},
            },
        ]
    }

    def _compare_output(self, json1, json2):
        # Remove keyIds since they are different for each run.
        for field in json2["fields"]:
            del field["keyId"]
        self.assertEqual(json1, json2)

    def test_show_encrypted_fields_map(self):
        self.maxDiff = None
        out = StringIO()
        call_command(
            "showencryptedfieldsmap",
            "--database",
            "encrypted",
            verbosity=0,
            stdout=out,
        )
        command_output = json_util.loads(out.getvalue())
        self._compare_output(
            self.expected_patient_record,
            command_output["encryption__patientrecord"],
        )

    def test_create_new_keys(self):
        self.maxDiff = None
        out = StringIO()
        call_command(
            "showencryptedfieldsmap",
            "--database",
            "encrypted",
            "--create-new-keys",
            verbosity=0,
            stdout=out,
        )
        command_output = json_util.loads(out.getvalue())
        self._compare_output(
            self.expected_patient_record,
            command_output["encryption__patientrecord"],
        )

        # Create a new connection to verify that the keys can be used in a
        # client-side configuration to migrate the encrypted fields.
        conn_params = connections["encrypted"].get_connection_params()
        auto_encryption_opts = AutoEncryptionOpts(
            key_vault_namespace="encryption.__keyvault",
            kms_providers={"local": {"key": os.urandom(96)}},
            encrypted_fields_map=command_output,
        )
        if conn_params.pop("auto_encryption_opts", False):
            # Call MongoClient instead of get_new_connection because
            # get_new_connection will return the encrypted connection from the
            # connection pool.
            with pymongo.MongoClient(**conn_params, auto_encryption_opts=auto_encryption_opts):
                call_command("migrate", "--database", "encrypted", verbosity=0)

        # TODO: Check the key vault to ensure that the keys created by
        # `showencryptedfieldsmap --create-new-keys` are in the key vault.
