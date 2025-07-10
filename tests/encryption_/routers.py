# routers.py


class TestEncryptedRouter:
    def db_for_read(self, model, **hints):
        if getattr(model, "encrypted", False):
            return f"{model.db_name}"
        return None

    def db_for_write(self, model, **hints):
        if getattr(model, "encrypted", False):
            return f"{model.db_name}"
        return None

    def allow_migrate(self, db, app_label, model_name=None, model=None, **hints):
        if getattr(model, "encrypted", False):
            return f"{model.db_name}"
        return None
