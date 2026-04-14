from django.db.migrations.operations.base import Operation


class AddEmbeddedField(Operation):
    def __init__(self, model_name, field_name):
        self.model_name = model_name
        self.field_name = field_name

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        model = to_state.apps.get_model(app_label, self.model_name)
        if self.allow_migrate_model(schema_editor.connection.alias, self.model_name):
            schema_editor.add_embedded_field(model, self.field_name)

    def deconstruct(self):
        name, args, kwargs = super().deconstruct()
        kwargs.update(
            {
                "column_prefix": self.column_prefix,
                "parent_model_name": self.parent_model_name,
            }
        )
        return name, args, kwargs
