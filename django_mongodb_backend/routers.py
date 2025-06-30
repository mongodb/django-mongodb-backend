from django.apps import apps

from django_mongodb_backend.models import EmbeddedModel


class MongoRouter:
    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        EmbeddedModels don't have their own collection and must be ignored by
        dumpdata.
        """
        if not model_name:
            return None
        try:
            model = apps.get_model(app_label, model_name)
        except LookupError:
            return None
        return False if issubclass(model, EmbeddedModel) else None


class EncryptionRouter:
    """
    Routes database operations for 'encrypted' models to the 'encryption' DB.
    """

    def db_for_read(self, model, **hints):
        if getattr(model, "encrypted_fields_map", False):
            return "encryption"
        return None

    def db_for_write(self, model, **hints):
        if getattr(model, "encrypted_fields_map", False):
            return "encryption"
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        Ensure that the 'encrypted' models only appear in the 'encryption' DB,
        and not in the default DB.
        """
        model = hints.get("model")
        if model and getattr(model, "encrypted_fields_map", False):
            return db == "encryption"
        return None
