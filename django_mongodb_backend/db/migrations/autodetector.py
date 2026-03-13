import contextlib

from django.core.exceptions import FieldDoesNotExist
from django.db import models
from django.db.migrations.autodetector import MigrationAutodetector as BaseMigrationAutodetector
from django.db.migrations.autodetector import OperationDependency

from django_mongodb_backend.db.migrations.operations import (
    AddEmbeddedField,
    AlterEmbeddedField,
    RemoveEmbeddedField,
    RenameEmbeddedField,
)
from django_mongodb_backend.indexes import FieldColumn


class MigrationAutodetector(BaseMigrationAutodetector):
    def _prepare_field_lists(self):
        super()._prepare_field_lists()

        def get_old_embedded_paths(field, name_prefix=None, path_prefix=None):
            if hasattr(field, "embedded_model"):
                if isinstance(field.embedded_model, str):
                    model_label = field.embedded_model
                else:
                    model_label = field.embedded_model._meta.label_lower
                model_lookup = tuple(model_label.split("."))
                embedded_model = self.from_state.models[
                    app_label,
                    self.renamed_models.get(model_lookup, model_lookup[1]),
                ]
                for subfield_name, subfield in embedded_model.fields.items():
                    if name_prefix:
                        name = f"{name_prefix}.{subfield_name}"
                    else:
                        name = f"{field.name}.{subfield_name}"
                    subfield_column = subfield.get_attname_column()[1]
                    if path_prefix:
                        path = f"{path_prefix}.{subfield_column}"
                    else:
                        field_column = field.get_attname_column()[1]
                        path = f"{field_column}.{subfield_column}"
                    self.old_embedded_field_keys[(app_label, model_name, name)] = path
                    # Check for nested embeds.
                    get_old_embedded_paths(subfield, name, path)

        self.old_embedded_field_keys = {}
        for app_label, model_name in self.kept_model_keys:
            for _field_name, field in self.from_state.models[
                app_label, self.renamed_models.get((app_label, model_name), model_name)
            ].fields.items():
                try:
                    if not self.to_state.models[app_label, model_name].options.get("managed", True):
                        continue
                except KeyError:
                    continue
                get_old_embedded_paths(field)

        def get_new_embedded_paths(field, name_prefix=None, path_prefix=None):
            if hasattr(field, "embedded_model"):
                embedded_model = self.to_state.models[tuple(field.embedded_model.split("."))]
                for subfield_name, subfield in embedded_model.fields.items():
                    subfield_column = subfield.get_attname_column()[1]
                    if name_prefix:
                        name = f"{name_prefix}.{subfield_name}"
                    else:
                        name = f"{field.name}.{subfield_name}"
                    if path_prefix:
                        path = f"{path_prefix}.{subfield_column}"
                    else:
                        field_column = field.get_attname_column()[1]
                        path = f"{field_column}.{subfield_column}"
                    self.new_embedded_field_keys[(app_label, model_name, name)] = path
                    get_new_embedded_paths(subfield, name, path)

        self.new_embedded_field_keys = {}
        for app_label, model_name in self.kept_model_keys:
            for _field_name, field in self.to_state.models[app_label, model_name].fields.items():
                if not self.to_state.models[app_label, model_name].options.get("managed", True):
                    continue
                get_new_embedded_paths(field)

    def generate_renamed_models(self):
        # Treat unmanaged models like managed models so that all migration
        # operations are generated for them, not just CreateModel/DeleteModel.
        # Obsolete once https://code.djangoproject.com/ticket/35813 is fixed.
        self.old_model_keys |= self.old_unmanaged_keys
        self.old_unmanaged_keys = set()
        self.new_model_keys |= self.new_unmanaged_keys
        self.new_unmanaged_keys = set()
        super().generate_renamed_models()

    def generate_removed_fields(self):
        super().generate_removed_fields()
        self.generate_renamed_embedded_fields()
        self.generate_removed_embedded_fields()

    def generate_altered_db_table(self):
        super().generate_altered_db_table()
        self.generate_added_embedded_fields()
        self.generate_altered_embedded_fields()

    def generate_added_embedded_fields(self):
        """Make AddEmbeddedField operations."""
        for app_label, model_name, field_name in sorted(
            set(self.new_embedded_field_keys) - set(self.old_embedded_field_keys)
        ):
            # If the embedded field was just added, then there's no need to
            # add each subfield.
            if "." in field_name:
                parent_field_name = field_name.rsplit(".", 1)[0]
                if (
                    app_label,
                    model_name,
                    parent_field_name,
                ) not in self.old_field_keys and (
                    app_label,
                    model_name,
                    parent_field_name,
                ) not in self.old_embedded_field_keys:
                    continue
            self._generate_added_embedded_field(app_label, model_name, field_name)

    def _generate_added_embedded_field(self, app_label, model_name, field_name):
        field = self.get_field(self.to_state.models[app_label, model_name], field_name)
        # Adding a field always depends at least on its removal.
        dependencies = [
            OperationDependency(app_label, model_name, field_name, OperationDependency.Type.REMOVE)
        ]
        # You can't just add NOT NULL fields with no default or fields
        # which don't allow empty strings as default.
        time_fields = (models.DateField, models.DateTimeField, models.TimeField)
        preserve_default = (
            field.null
            or field.has_default()
            or (field.blank and field.empty_strings_allowed)
            or (isinstance(field, time_fields) and field.auto_now)
        )
        if not preserve_default:
            field = field.clone()
            if isinstance(field, time_fields) and field.auto_now_add:
                field.default = self.questioner.ask_auto_now_add_addition(field_name, model_name)
            else:
                field.default = self.questioner.ask_not_null_addition(field_name, model_name)
        if field.unique and field.has_default() and callable(field.default):
            self.questioner.ask_unique_callable_default_addition(field_name, model_name)
        self.add_operation(
            app_label,
            AddEmbeddedField(
                model_name=model_name,
                name=self.new_embedded_field_keys[app_label, model_name, field_name],
                field=field,
                preserve_default=preserve_default,
            ),
            dependencies=dependencies,
        )

    def generate_renamed_embedded_fields(self):
        """
        Make RenameEmbeddedField operations for renamed embedded leaf fields.
        """
        # Build inverse of renamed_fields: (app_label, model_name, old_name) ->
        # new_name.
        renamed_field_inverse = {
            (al, mn, old): new for (al, mn, new), old in self.renamed_fields.items()
        }
        for app_label, model_name, old_attr_path in sorted(
            set(self.old_embedded_field_keys) - set(self.new_embedded_field_keys)
        ):
            *parents, leaf_field_name = old_attr_path.split(".")
            # Navigate the from_state to find the model containing the leaf
            # field.
            current_app_label = app_label
            current_model_name = model_name
            for part in parents:
                field = self.from_state.models[current_app_label, current_model_name].get_field(
                    part
                )
                if hasattr(field, "embedded_model"):
                    label_parts = field.embedded_model.split(".")
                    if len(label_parts) == 2:
                        current_app_label, current_model_name = label_parts
                    else:
                        current_model_name = label_parts[0]
            # Check if the leaf field was renamed.
            new_leaf_field_name = renamed_field_inverse.get(
                (current_app_label, current_model_name, leaf_field_name)
            )
            if new_leaf_field_name is None:
                continue
            new_attr_path = ".".join([*parents, new_leaf_field_name])
            if (app_label, model_name, new_attr_path) not in self.new_embedded_field_keys:
                continue
            self._generate_renamed_embedded_field(
                app_label,
                model_name,
                old_attr_path,
                new_attr_path,
                current_app_label,
                current_model_name,
                new_leaf_field_name,
            )
            # Remove from both dicts so remove/add generators skip these paths.
            del self.old_embedded_field_keys[app_label, model_name, old_attr_path]
            del self.new_embedded_field_keys[app_label, model_name, new_attr_path]

    def _generate_renamed_embedded_field(
        self,
        app_label,
        model_name,
        old_attr_path,
        new_attr_path,
        leaf_app_label,
        leaf_model_name,
        leaf_new_field_name,
    ):
        self.add_operation(
            app_label,
            RenameEmbeddedField(
                model_name=model_name,
                old_name=old_attr_path,
                new_name=new_attr_path,
            ),
        )

    def generate_removed_embedded_fields(self):
        """Make RemoveEmbeddedField operations."""
        for app_label, model_name, field_name in sorted(
            set(self.old_embedded_field_keys) - set(self.new_embedded_field_keys)
        ):
            self._generate_removed_embedded_field(app_label, model_name, field_name)

    def _generate_removed_embedded_field(self, app_label, model_name, field_name):
        self.add_operation(
            app_label,
            RemoveEmbeddedField(
                model_name=model_name,
                name=field_name,
            ),
        )

    def generate_altered_embedded_fields(self):
        """
        Make AlterEmbeddedField operations when an embedded column path
        changes.
        """
        common = set(self.old_embedded_field_keys) & set(self.new_embedded_field_keys)
        for app_label, model_name, field_name in sorted(common):
            old_path = self.old_embedded_field_keys[app_label, model_name, field_name]
            new_path = self.new_embedded_field_keys[app_label, model_name, field_name]
            if old_path != new_path:
                self._generate_altered_embedded_field(app_label, model_name, field_name)

    def _generate_altered_embedded_field(self, app_label, model_name, field_name):
        field = self.get_field(self.to_state.models[app_label, model_name], field_name)
        # Navigate the path to locate the leaf embedded model for the ALTER
        # dependency.
        *parents, leaf_field_name = field_name.split(".")
        current_app_label = app_label
        current_model_name = model_name
        for part in parents:
            parent_field = self.to_state.models[current_app_label, current_model_name].get_field(
                part
            )
            if hasattr(parent_field, "embedded_model"):
                label_parts = parent_field.embedded_model.split(".")
                if len(label_parts) == 2:
                    current_app_label, current_model_name = label_parts
                else:
                    current_model_name = label_parts[0]
        self.add_operation(
            app_label,
            AlterEmbeddedField(
                model_name=model_name,
                name=field_name,
                field=field,
            ),
            dependencies=[
                OperationDependency(
                    current_app_label,
                    current_model_name,
                    leaf_field_name,
                    OperationDependency.Type.ALTER,
                )
            ],
        )

    def get_field(self, model, field_name):
        """
        A version of ModelState.get_field() that can retrieve embedded model
        fields.
        """
        path = []
        base_model = model
        *parents, leaf = field_name.split(".")
        for i, name in enumerate(parents):
            field = model.get_field(name)
            path.append(getattr(field, "column", field.get_attname_column()[1]))
            # For EmbeddedModelFields, advance to the embedded model and
            # continue to loop, searching for the next field.
            if hasattr(field, "embedded_model"):
                model_lookup = tuple(field.embedded_model.split("."))
                model = self.to_state.models[model_lookup]
            # For PolymorphicEmbeddedModelFields, recurse into each embedded
            # model until the field is found.
            elif embedded_models := getattr(field, "embedded_models", None):
                for submodel in embedded_models:
                    with contextlib.suppress(FieldDoesNotExist):
                        subfield = self.get_field(submodel, ".".join([*parents[i + 1 :], leaf]))
                        path.extend(subfield.column.split("."))
                        return FieldColumn(subfield.field, ".".join(path))
                raise FieldDoesNotExist(
                    f"The models of field '{'.'.join(parents)}' have no field named '{leaf}'."
                )
            else:
                raise FieldDoesNotExist(f"{base_model.__name__} has no field named '{field_name}'.")
        # Add the final field.
        return model.get_field(leaf)
