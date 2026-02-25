from django.db import connections


def get_mongodb_connection():
    for alias in connections:
        if connections[alias].vendor == "mongodb":
            return connections[alias]
    return None


def serialize_model_reference(model):
    """Serialize a model to its label for use in migrations."""
    if isinstance(model, str):
        # For "app_label.Model", lowercase the model name only.
        if "." in model:
            app_label, model_name = model.split(".")
            return f"{app_label}.{model_name.lower()}"
        # For "Model", lowercase it.
        return model.lower()
    return model._meta.label_lower
