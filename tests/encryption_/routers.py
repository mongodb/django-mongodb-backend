class TestEncryptedRouter:
    """Router for testing encrypted models in Django. `kms_provider`
    must be set on the global test router since table creation happens
    at the start of the test suite, before @override_settings(
    DATABASE_ROUTERS=[TestEncryptedRouter()]) takes effect.
    """

    def allow_migrate(self, db, app_label, model_name=None, model=None, **hints):
        return getattr(model, "encrypted", False)

    def db_for_read(self, model, **hints):
        if getattr(model, "encrypted", False):
            return "my_encrypted_database"
        return None

    db_for_write = db_for_read
