from itertools import chain

from django.apps import apps
from django.core.checks import Tags, register
from django.db import connections, router


def check_indexes(app_configs, databases=None, **kwargs):  # noqa: ARG001
    """
    Call Index.check() on all model indexes.

    This function will be obsolete when Django calls Index.check() after
    https://code.djangoproject.com/ticket/36273.
    """
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
                if hasattr(model_index, "check"):
                    errors.extend(model_index.check(model, connection))
    return errors


def register_checks():
    register(check_indexes, Tags.models)
