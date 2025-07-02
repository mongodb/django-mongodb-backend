from django.db import connection


class EncryptedRouter:
    """
    Routes database operations for encrypted models to the encrypted DB.
    """

    def db_for_read(self, model, **hints):
        with connection.schema_editor() as editor:
            if model and getattr(editor._get_encrypted_fields_map(model), False):
                return "encrypted"
        return None

    def db_for_write(self, model, **hints):
        with connection.schema_editor() as editor:
            if model and getattr(editor._get_encrypted_fields_map(model), False):
                return "encrypted"
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        model = hints.get("model")
        with connection.schema_editor() as editor:
            if model and getattr(editor._get_encrypted_fields_map(model), False):
                return db == "encrypted"
        return None
