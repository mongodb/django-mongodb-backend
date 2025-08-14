from bson import json_util
from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import DEFAULT_DB_ALIAS, connections, router

from django_mongodb_backend.model_utils import model_has_encrypted_fields


class Command(BaseCommand):
    help = """
    This command shows the mapping of encrypted fields to attributes
    including  data type, data keys and query types. It can be used to set the
    ``encrypted_fields_map`` in ``AutoEncryptionOpts``. Defaults to showing
    existing keys from the configured key vault.
    """

    def add_arguments(self, parser):
        parser.add_argument(
            "--database",
            default=DEFAULT_DB_ALIAS,
            help="""
            Specifies the database to use. Defaults to ``default``.""",
        )
        parser.add_argument(
            "--create-data-keys",
            action="store_true",
            help="""
            If specified, this option will create and show new encryption
            keys instead of showing existing keys from the configured key vault.
            """,
        )

    def handle(self, *args, **options):
        db = options["database"]
        create_data_keys = options.get("create_data_keys", False)
        connection = connections[db]
        client = connection.connection
        encrypted_fields_map = {}
        with connection.schema_editor() as editor:
            for app_config in apps.get_app_configs():
                for model in router.get_migratable_models(app_config, db):
                    if model_has_encrypted_fields(model):
                        fields = editor._get_encrypted_fields_map(
                            model, client, create_data_keys=create_data_keys
                        )
                        encrypted_fields_map[model._meta.db_table] = fields
        self.stdout.write(json_util.dumps(encrypted_fields_map, indent=2))
