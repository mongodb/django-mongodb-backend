import json

from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import DEFAULT_DB_ALIAS, connections, router


class Command(BaseCommand):
    help = "Generate a `schema_map` of encrypted fields for all encrypted"
    " models in the database for use with `AutoEncryptionOpts` in"
    " production environments."

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
        schema_map = self.get_encrypted_fields_map(connection)
        self.stdout.write(json.dumps(schema_map, indent=2))

    def get_encrypted_fields_map(self, connection):
        schema_map = {}
        for app_config in apps.get_app_configs():
            for model in router.get_migratable_models(
                app_config, connection.alias, include_auto_created=False
            ):
                if getattr(model, "encrypted", False):
                    app_label = model._meta.app_label
                    collection_name = model._meta.db_table
                    namespace = f"{app_label}.{collection_name}"
                    fields = list(connection.schema_editor()._get_encrypted_fields_map(model))
                    if fields:
                        schema_map[namespace] = {"fields": fields}
        return schema_map
