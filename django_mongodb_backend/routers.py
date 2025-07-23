from django.apps import apps
from django.core.exceptions import ImproperlyConfigured
from django.db.utils import ConnectionRouter


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

        # Delay import for `register_routers` patching.
        from django_mongodb_backend.models import EmbeddedModel

        return False if issubclass(model, EmbeddedModel) else None


def kms_provider(self, model, *args, **kwargs):
    for router in self.routers:
        func = getattr(router, "kms_provider", None)
        if func and callable(func):
            result = func(model, *args, **kwargs)
            if result is not None:
                return result
    if getattr(model, "encrypted", False):
        raise ImproperlyConfigured("No kms_provider found in database router.")
    return None


def register_routers():
    """
    Patch the ConnectionRouter to use the custom kms_provider method.
    """
    ConnectionRouter.kms_provider = kms_provider
