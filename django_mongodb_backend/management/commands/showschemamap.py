from bson import json_util
from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import DEFAULT_DB_ALIAS, connections, router
from pymongo.encryption import ClientEncryption

from django_mongodb_backend.fields import has_encrypted_fields


class Command(BaseCommand):
    help = "Generate a `schema_map` of encrypted fields for all encrypted"
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
            "--kms-provider",
            default="local",
            help="Specify the KMS provider to use for encryption. Defaults to 'local'.",
        )

    def handle(self, *args, **options):
        db = options["database"]
        connection = connections[db]
        schema_map = {}
        for app_config in apps.get_app_configs():
            for model in app_config.get_models():
                if has_encrypted_fields(model):
                    fields = connection.schema_editor()._get_encrypted_fields_map(model)
                    client = connection.connection
                    options = client._options.auto_encryption_opts
                    ce = ClientEncryption(
                        options._kms_providers,
                        options._key_vault_namespace,
                        client,
                        client.codec_options,
                    )
                    kms_provider = router.kms_provider(model)
                    master_key = connection.settings_dict.get("KMS_CREDENTIALS").get(kms_provider)
                    for field in fields["fields"]:
                        data_key = ce.create_data_key(
                            kms_provider=kms_provider,
                            master_key=master_key,
                        )
                        field["keyId"] = data_key
                    schema_map[model._meta.db_table] = fields
        self.stdout.write(json_util.dumps(schema_map, indent=2))
