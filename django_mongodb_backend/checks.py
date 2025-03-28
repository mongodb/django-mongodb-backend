from itertools import chain

from django.apps import apps
from django.core.checks import Tags, register
from django.db import connections, router

from django_mongodb_backend.indexes import VectorSearchIndex


@register(Tags.models)
def check_vector_search_indexes(app_configs, databases=None, **kwargs):  # noqa: ARG001
    errors = []
    if app_configs is None:
        models = apps.get_models()
    else:
        models = chain.from_iterable(app_config.get_models() for app_config in app_configs)
    for model in models:
        for db in databases or ():
            if not router.allow_migrate_model(db, model):
                continue
            connection = connections[db]
            for model_index in model._meta.indexes:
                if not isinstance(model_index, VectorSearchIndex):
                    continue
                errors.extend(model_index.check(model, connection))
    return errors
