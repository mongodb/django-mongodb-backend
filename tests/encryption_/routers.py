class EncryptedRouter:
    """
    Routes database operations for encrypted models to the encrypted DB.
    """

    def db_for_read(self, model, **hints):
        return "encrypted"

    def db_for_write(self, model, **hints):
        return "encrypted"

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        return "encrypted"
