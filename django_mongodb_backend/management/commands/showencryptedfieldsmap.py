from bson import json_util
from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import DEFAULT_DB_ALIAS, connections, router

from django_mongodb_backend.model_utils import model_has_encrypted_fields


class Command(BaseCommand):
    help = "Generate an `encrypted_fields_map` of encrypted fields for all encrypted"
    " models in the database for use with `AutoEncryptionOpts` in"
    " client configuration."

    def add_arguments(self, parser):
        parser.add_argument(
            "--database",
            default=DEFAULT_DB_ALIAS,
            help="Specify the database to use for generating the encrypted"
            "fields map. Defaults to the 'default' database.",
        )
        parser.add_argument(
            "--create-new-keys",
            action="store_true",
            help="Create the encrypted fields map.",
        )

    def handle(self, *args, **options):
        db = options["database"]
        create = options.get("create", False)
        connection = connections[db]
        client = connection.connection
        encrypted_fields_map = {}
        auto_encryption_opts = getattr(client._options, "auto_encryption_opts", None)
        for app_config in apps.get_app_configs():
            for model in router.get_migratable_models(app_config, db):
                if model_has_encrypted_fields(model):
                    from_db = not create
                    fields = connection.schema_editor()._get_encrypted_fields_map(
                        model, client, auto_encryption_opts, from_db=from_db
                    )
                    encrypted_fields_map[model._meta.db_table] = fields
        self.stdout.write(json_util.dumps(encrypted_fields_map, indent=2))
