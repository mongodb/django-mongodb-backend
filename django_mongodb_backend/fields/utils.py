from django.db import connections


def serialize_to_python(obj, serializer, *, polymorphic=False):
    data = {
        field.name: serializer._value_from_field(obj, field) for field in obj._meta.local_fields
    }
    if polymorphic:
        data["_label"] = obj._meta.label
    return data


def deserialize_from_python(value, *, field=None, model=None):
    """
    Deserialize `value` (a dictionary) into a model instance.

    For homogeneous embedded model fields, the model class is specified by the
    `model` kwarg.
    """
    if model is None:
        # For polymorphic embedded model fields, the model class is specified
        # by the  "_label" in the `value`.
        # field._get_model_from_label().
        label = value.pop("_label")
        # In which case `field` must be specified so that the model class
        # can be looked up.
        model = field._get_model_from_label(label)
    subdata = {}
    for subfield_name, subvalue in value.items():
        subfield = model._meta.get_field(subfield_name)
        subdata[subfield.name] = subfield.to_python(subvalue)
    return model(**subdata)


def serialize_to_xml(obj, serializer):
    serializer.start_object(obj)
    if obj is None:
        serializer.xml.addQuickElement("None")
    else:
        for field in obj._meta.local_fields:
            serializer.handle_field(obj, field)
    serializer.end_object(obj)


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
