from django.db.migrations.operations import AddField, RemoveField


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
        model_key = (app_label, self.model_name_lower)
        state.reload_model(*model_key)

    def state_backwards(self, app_label, state):
        model_key = (app_label, self.model_name_lower)
        state.reload_model(*model_key)


#        state.add_field(
#            app_label,
#            self.model_name_lower,
#            self.name,
#            self.field,
#            self.preserve_default,
#        )

#    def add_field(self, app_label, model_name, name, field, preserve_default):
# If preserve default is off, don't use the default for future state.
#        if not preserve_default:
#            field = field.clone()
#            field.default = NOT_PROVIDED
#        else:
#            field = field
#        model_key = app_label, model_name
#        self.models[model_key].fields[name] = field
#        if self._relations is not None:
#            self.resolve_model_field_relations(model_key, name, field)
# Delay rendering of relationships if it's not a relational field.
#        delay = not field.is_relation
#        self.reload_model(*model_key) #, delay=delay)


class RemoveEmbeddedField(RemoveField):
    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        from_model = from_state.apps.get_model(app_label, self.model_name)
        if self.allow_migrate_model(schema_editor.connection.alias, from_model):
            # TODO: Does "self.name" account for db_column?
            schema_editor.remove_embedded_field(from_model, self.name)

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        model = to_state.apps.get_model(app_label, self.model_name)
        if self.allow_migrate_model(schema_editor.connection.alias, model):
            schema_editor.add_embedded_field(model, self.name, self.field)

    def describe(self):
        return f"Remove embedded field {self.name} from {self.model_name}"

    def state_forwards(self, app_label, state):
        model_key = (app_label, self.model_name_lower)
        state.reload_model(*model_key)

    def state_backwards(self, app_label, state):
        model_key = (app_label, self.model_name_lower)
        state.reload_model(*model_key)
