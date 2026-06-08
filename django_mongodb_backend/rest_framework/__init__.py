try:
    from .serializers import EmbeddedModelSerializer, MongoModelSerializer
except ModuleNotFoundError as exc:
    if exc.name == "rest_framework":
        raise ModuleNotFoundError(
            "djangorestframework is required to use django_mongodb_backend.rest_framework. "
            "Install it with: pip install 'django-mongodb-backend[rest_framework]'"
        ) from exc
    raise

__all__ = ["EmbeddedModelSerializer", "MongoModelSerializer"]
