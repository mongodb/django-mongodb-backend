from django.db.migrations.autodetector import MigrationAutodetector as BaseMigrationAutodetector


class MigrationAutodetector(BaseMigrationAutodetector):
    def generate_renamed_models(self):
        # Treat unmanaged models like managed models so that all migration
        # operations are generated for them, not just CreateModel/DeleteModel.
        # Obsolete once https://code.djangoproject.com/ticket/35813 is fixed.
        self.old_model_keys |= self.old_unmanaged_keys
        self.old_unmanaged_keys = set()
        self.new_model_keys |= self.new_unmanaged_keys
        self.new_unmanaged_keys = set()
        super().generate_renamed_models()
