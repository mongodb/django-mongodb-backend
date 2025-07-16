class TestEncryptedRouter:
    def allow_migrate(self, db, app_label, model_name=None, model=None, **hints):
        return getattr(model, "encrypted", False)

    def db_for_read(self, model, **hints):
        if getattr(model, "encrypted", False):
            return "encrypted"
        return None

    db_for_write = db_for_read

    # FIXME: Possibly because it is patched in routers.py, this is not called
    # from schema.py.
    def kms_provider(self, model):
        return "aws"
