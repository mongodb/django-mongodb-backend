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
