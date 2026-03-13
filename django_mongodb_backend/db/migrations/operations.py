from django.db.migrations.operations import AddField, AlterField, RemoveField, RenameField
from django.db.models import NOT_PROVIDED

from django_mongodb_backend.indexes import get_field


class AddEmbeddedField(AddField):
    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        to_model = to_state.apps.get_model(app_label, self.model_name)
        if self.allow_migrate_model(schema_editor.connection.alias, to_model):
            schema_editor.add_embedded_field(to_model, self.name, self.field)

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        from_model = from_state.apps.get_model(app_label, self.model_name)
        if self.allow_migrate_model(schema_editor.connection.alias, from_model):
            # TODO: Does "self.name" account for db_column?
            schema_editor.remove_embedded_field(from_model, self.name)

    def describe(self):
        return f"Add embedded field {self.name} to {self.model_name}"

    def state_forwards(self, app_label, state):
        # If preserve default is off, don't use the default for future state.
        if not self.preserve_default:
            field = self.field.clone()
            field.default = NOT_PROVIDED
        else:
            field = self.field
        model_key = (app_label, self.model_name_lower)
        state.reload_model(*model_key)

    def state_backwards(self, app_label, state):
        model_key = (app_label, self.model_name_lower)
        state.reload_model(*model_key)


def _embedded_column_path(state, app_label, model_name, attr_path):
    """
    Resolve a dotted Python attribute path to a dotted db_column path using
    state.models directly, avoiding stale class references from the app registry.
    """
    columns = []
    current_app_label = app_label
    current_model_name = model_name.lower()
    for part in attr_path.split("."):
        model_state = state.models[current_app_label, current_model_name]
        field = model_state.fields[part]
        columns.append(field.db_column or part)
        if hasattr(field, "embedded_model"):
            emb = field.embedded_model
            if not isinstance(emb, str):
                current_app_label = emb._meta.app_label
                current_model_name = emb.__name__.lower()
            elif "." in emb:
                current_app_label, emb = emb.rsplit(".", 1)
                current_model_name = emb.lower()
            else:
                current_model_name = emb.lower()
    return ".".join(columns)


class AlterEmbeddedField(AlterField):
    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        to_model = to_state.apps.get_model(app_label, self.model_name)
        if self.allow_migrate_model(schema_editor.connection.alias, to_model):
            schema_editor.alter_embedded_field(
                to_model,
                _embedded_column_path(from_state, app_label, self.model_name, self.name),
                _embedded_column_path(to_state, app_label, self.model_name, self.name),
            )

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        self.database_forwards(app_label, schema_editor, from_state, to_state)

    def describe(self):
        return f"Alter embedded field {self.name} on {self.model_name}"

    def state_forwards(self, app_label, state):
        model_key = (app_label, self.model_name_lower)
        state.reload_model(*model_key)

    def state_backwards(self, app_label, state):
        model_key = (app_label, self.model_name_lower)
        state.reload_model(*model_key)


class RenameEmbeddedField(RenameField):
    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        to_model = to_state.apps.get_model(app_label, self.model_name)
        if self.allow_migrate_model(schema_editor.connection.alias, to_model):
            schema_editor.alter_embedded_field(
                to_model,
                _embedded_column_path(from_state, app_label, self.model_name, self.old_name),
                _embedded_column_path(to_state, app_label, self.model_name, self.new_name),
            )

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        to_model = to_state.apps.get_model(app_label, self.model_name)
        if self.allow_migrate_model(schema_editor.connection.alias, to_model):
            schema_editor.alter_embedded_field(
                to_model,
                _embedded_column_path(from_state, app_label, self.model_name, self.new_name),
                _embedded_column_path(to_state, app_label, self.model_name, self.old_name),
            )

    def describe(self):
        return f"Rename embedded field {self.old_name} on {self.model_name} to {self.new_name}"

    def state_forwards(self, app_label, state):
        model_key = (app_label, self.model_name_lower)
        state.reload_model(*model_key)

    def state_backwards(self, app_label, state):
        model_key = (app_label, self.model_name_lower)
        state.reload_model(*model_key)


class RemoveEmbeddedField(RemoveField):
    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        from_model = from_state.apps.get_model(app_label, self.model_name)
        if self.allow_migrate_model(schema_editor.connection.alias, from_model):
            # TODO: Does "self.name" account for db_column?
            schema_editor.remove_embedded_field(from_model, self.name)

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        model = to_state.apps.get_model(app_label, self.model_name)
        if self.allow_migrate_model(schema_editor.connection.alias, model):
            field = get_field(model, self.name).field
            schema_editor.add_embedded_field(model, self.name, field)

    def describe(self):
        return f"Remove embedded field {self.name} from {self.model_name}"

    def state_forwards(self, app_label, state):
        model_key = (app_label, self.model_name_lower)
        state.reload_model(*model_key)

    def state_backwards(self, app_label, state):
        model_key = (app_label, self.model_name_lower)
        state.reload_model(*model_key)
