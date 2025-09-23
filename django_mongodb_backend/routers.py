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
    Return the Key Management Service (KMS) provider for a given model.

    Call each router's kms_provider() method (if present), and return the
    first non-None result. Raise ImproperlyConfigured if no provider is found.
    """
    for router in self.routers:
        func = getattr(router, "kms_provider", None)
        if func and callable(func) and (result := func(model, *args, **kwargs)):
            return result
    raise ImproperlyConfigured("No kms_provider found in database routers.")


def register_routers():
    ConnectionRouter.kms_provider = kms_provider
