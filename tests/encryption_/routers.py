from django_mongodb_backend.model_utils import model_has_encrypted_fields


class TestEncryptedRouter:
    """Router for testing encrypted models in Django. `kms_provider`
    must be set on the global test router since table creation happens
    at the start of the test suite, before @override_settings(
    DATABASE_ROUTERS=[TestEncryptedRouter()]) takes effect.
    """

    def allow_migrate(self, db, app_label, model_name=None, model=None, **hints):
        if model:
            return db == ("encrypted" if model_has_encrypted_fields(model) else "default")
        return db == "default"

    def db_for_read(self, model, **hints):
        if model_has_encrypted_fields(model):
            return "encrypted"
        return "default"

    db_for_write = db_for_read

    def kms_provider(self, model, **hints):
        return "local"
