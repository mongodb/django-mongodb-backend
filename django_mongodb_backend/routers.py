from django.apps import apps
from django.core.exceptions import ImproperlyConfigured
from django.db.utils import ConnectionRouter


class MongoRouter:
    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        EmbeddedModels don't have their own collection and must be ignored by
        dumpdata.
        """
        from django_mongodb_backend.models import EmbeddedModel  # noqa: PLC0415

        if not model_name:
            return None
        try:
            model = apps.get_model(app_label, model_name)
        except LookupError:
            return None
        return False if issubclass(model, EmbeddedModel) else None


# This function is intended to be monkey-patched as a method of ConnectionRouter.
def kms_provider(self, model, *args, **kwargs):
    """
    Monkey-patched method for ConnectionRouter to resolve a KMS provider for a given model.
    Iterates through all configured database routers, calling their `kms_provider` method (if present)
    to determine the appropriate Key Management Service (KMS) provider for the specified model.
    Returns the first non-None result found. Raises ImproperlyConfigured if no provider is found.
    """
    for router in self.routers:
        func = getattr(router, "kms_provider", None)
        if func and callable(func):
            result = func(model, *args, **kwargs)
            if result is not None:
                return result
    raise ImproperlyConfigured("No kms_provider found in database router.")


def register_routers():
    ConnectionRouter.kms_provider = kms_provider
