from django.apps import apps
from django.core.exceptions import ImproperlyConfigured
from django.db.utils import ConnectionRouter

from .fields import has_encrypted_fields


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


def kms_provider(self, model, *args, **kwargs):
    for router in self.routers:
        func = getattr(router, "kms_provider", None)
        if func and callable(func):
            result = func(model, *args, **kwargs)
            if result is not None:
                return result
    if has_encrypted_fields(model):
        raise ImproperlyConfigured("No kms_provider found in database router.")
    return None


def register_routers():
    """
    Patch the ConnectionRouter to use the custom kms_provider method.
    """
    ConnectionRouter.kms_provider = kms_provider
