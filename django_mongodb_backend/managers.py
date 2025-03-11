from django.db import NotSupportedError
from django.db.models.manager import BaseManager

from .queryset import MongoQuerySet, MultiMongoQuerySet


class MongoManager(BaseManager.from_queryset(MongoQuerySet)):
    pass


class MultiMongoManager(BaseManager.from_queryset(MultiMongoQuerySet)):
    def get_queryset(self):
        return super().get_queryset().filter(_t__in=self.model.subclasses())


class EmbeddedModelManager(BaseManager):
    """
    Prevent all queryset operations on embedded models since they don't have
    their own collection.

    Raise a helpful error message for some basic QuerySet methods. Subclassing
    BaseManager means that other methods raise, e.g. AttributeError:
    'EmbeddedModelManager' object has no attribute 'update_or_create'".
    """

    def all(self):
        raise NotSupportedError("EmbeddedModels cannot be queried.")

    def get(self, *args, **kwargs):
        raise NotSupportedError("EmbeddedModels cannot be queried.")

    def filter(self, *args, **kwargs):
        raise NotSupportedError("EmbeddedModels cannot be queried.")

    def create(self, **kwargs):
        raise NotSupportedError("EmbeddedModels cannot be created.")

    def update(self, *args, **kwargs):
        raise NotSupportedError("EmbeddedModels cannot be updated.")

    def delete(self):
        raise NotSupportedError("EmbeddedModels cannot be deleted.")
