from django.apps import apps
from django.db.utils import ConnectionRouter

from .encryption import KMS_CREDENTIALS


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


def kms_credentials(self, provider):  # noqa: ARG001
    return KMS_CREDENTIALS.get(provider, None)


def register_routers():
    """
    Patch the ConnectionRouter with methods to get KMS credentials and provider
    from the SchemaEditor.
    """
    ConnectionRouter.kms_credentials = kms_credentials
    ConnectionRouter.kms_provider = ConnectionRouter._router_func("kms_provider")
