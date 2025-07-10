import json

from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import DEFAULT_DB_ALIAS, connections, router


class Command(BaseCommand):
    help = "Generate an encryptedFieldsMap for MongoDB automatic encryption"

    def add_arguments(self, parser):
        parser.add_argument(
            "--database",
            default=DEFAULT_DB_ALIAS,
            help="Specify the database to use for generating the encrypted"
            "fields map. Defaults to the 'default' database.",
        )

    def handle(self, *args, **options):
        db = options["database"]
        connection = connections[db]

        schema_map = self.generate_encrypted_fields_schema_map(connection)

        self.stdout.write(json.dumps(schema_map, indent=2))

    def generate_encrypted_fields_schema_map(self, conn):
        schema_map = {}

        for app_config in apps.get_app_configs():
            for model in router.get_migratable_models(
                app_config, conn.alias, include_auto_created=False
            ):
                if getattr(model, "encrypted", False):
                    encrypted_fields = self.get_encrypted_fields(model, conn)
                    if encrypted_fields:
                        collection = model._meta.db_table
                        schema_map[collection] = {"fields": encrypted_fields}

        return schema_map

    def get_encrypted_fields(self, model, conn):
        return conn.schema_editor()._get_encrypted_fields_map(model)
