def model_has_encrypted_fields(model):
    return any(getattr(field, "encrypted", False) for field in model._meta.fields)
