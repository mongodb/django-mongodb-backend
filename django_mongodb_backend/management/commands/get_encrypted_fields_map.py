from bson import json_util
from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import DEFAULT_DB_ALIAS, connections, router
from pymongo.encryption import ClientEncryption


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
        parser.add_argument(
            "--kms-provider",
            default="local",
            help="Specify the KMS provider to use for encryption. Defaults to 'local'.",
        )

    def handle(self, *args, **options):
        db = options["database"]
        kms_provider = options["kms_provider"]
        connection = connections[db]
        schema_map = json_util.dumps(
            self.get_encrypted_fields_map(connection, kms_provider), indent=2
        )
        self.stdout.write(schema_map)

    def get_client_encryption(self, connection):
        client = connection.connection
        options = client._options.auto_encryption_opts
        key_vault_namespace = options._key_vault_namespace
        kms_providers = options._kms_providers
        return ClientEncryption(kms_providers, key_vault_namespace, client, client.codec_options)

    def get_encrypted_fields_map(self, connection, kms_provider):
        schema_map = {}
        for app_config in apps.get_app_configs():
            for model in router.get_migratable_models(
                app_config, connection.settings_dict["NAME"], include_auto_created=False
            ):
                if getattr(model, "encrypted", False):
                    fields = connection.schema_editor()._get_encrypted_fields_map(model)
                    ce = self.get_client_encryption(connection)
                    master_key = connection.settings_dict.get("KMS_CREDENTIALS").get(kms_provider)
                    # Via PyMongo's ClientEncryption
                    for i, field in enumerate(fields["fields"]):  # noqa: B007
                        data_key = ce.create_data_key(
                            kms_provider=kms_provider,
                            master_key=master_key,
                        )
                        fields["fields"][i]["keyId"] = data_key
                    schema_map[model._meta.db_table] = fields
        return schema_map
