import json

from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import DEFAULT_DB_ALIAS, connections


class Command(BaseCommand):
    help = "Generate an encryptedFieldsMap for MongoDB automatic encryption"

    def handle(self, *args, **options):
        connection = connections[DEFAULT_DB_ALIAS]

        schema_map = self.generate_encrypted_fields_schema_map(connection)

        self.stdout.write(json.dumps(schema_map, indent=2))

    def generate_encrypted_fields_schema_map(self, conn):
        schema_map = {}

        for model in apps.get_models():
            if getattr(model, "encrypted", False):
                encrypted_fields = self.get_encrypted_fields(model, conn)
                if encrypted_fields:
                    collection = model._meta.db_table
                    schema_map[collection] = {"fields": encrypted_fields}

        return schema_map

    def get_encrypted_fields(self, model, conn):
        encrypted_fields = []

        with conn.schema_editor() as editor:
            field_map = editor._get_encrypted_fields_map(model)
            encrypted_fields.append(field_map)

        return encrypted_fields
