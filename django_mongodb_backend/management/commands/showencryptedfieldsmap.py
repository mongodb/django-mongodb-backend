from bson import json_util
from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import DEFAULT_DB_ALIAS, connections, router

from django_mongodb_backend.utils import model_has_encrypted_fields


class Command(BaseCommand):
    help = "Shows the encrypted_fields_map for use in AutoEncryptionOpts."

    def add_arguments(self, parser):
        parser.add_argument(
            "--database",
            default=DEFAULT_DB_ALIAS,
            help='Specifies the database to use. Defaults to the "default" database.',
        )

    def handle(self, *args, **options):
        db = options["database"]
        connection = connections[db]
        connection.ensure_connection()
        encrypted_fields_map = {}
        with connection.schema_editor() as editor:
            for app_config in apps.get_app_configs():
                for model in router.get_migratable_models(app_config, db):
                    if model_has_encrypted_fields(model) and model._meta.can_migrate(connection):
                        fields = editor._get_encrypted_fields(model, create_data_keys=False)
                        encrypted_fields_map[model._meta.db_table] = fields
        self.stdout.write(json_util.dumps(encrypted_fields_map, indent=4))
