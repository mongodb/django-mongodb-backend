from django.db.migrations.state import ProjectState
from django.test import TestCase

from django_mongodb_backend.db.migrations.autodetector import MigrationAutodetector


class BaseAutodetectorTests(TestCase):
    # Base class copied from Django's tests/migrations/test_autodetector.py.
    def repr_changes(self, changes, include_dependencies=False):
        output = ""
        for app_label, migrations_ in sorted(changes.items()):
            output += f"  {app_label}:\n"
            for migration in migrations_:
                output += f"    {migration.name}\n"
                for operation in migration.operations:
                    output += f"      {operation}\n"
                if include_dependencies:
                    output += "      Dependencies:\n"
                    if migration.dependencies:
                        for dep in migration.dependencies:
                            output += f"        {dep}\n"
                    else:
                        output += "        None\n"
        return output

    def assertNumberMigrations(self, changes, app_label, number):
        if len(changes.get(app_label, [])) != number:
            num_migrations = len(changes.get(app_label, []))
            self.fail(
                f"Incorrect number of migrations ({num_migrations}) for "
                f"{app_label} (expected {number})\n{self.repr_changes(changes)}"
            )

    def assertMigrationDependencies(self, changes, app_label, position, dependencies):
        if not changes.get(app_label):
            self.fail(f"No migrations found for {app_label}\n{self.repr_changes(changes)}")
        if len(changes[app_label]) < position + 1:
            self.fail(
                f"No migration at index {position} for {app_label}\n{self.repr_changes(changes)}"
            )
        migration = changes[app_label][position]
        if set(migration.dependencies) != set(dependencies):
            self.fail(
                f"Migration dependencies mismatch for {app_label}.{migration.name} "
                f"(expected {dependencies}):\n"
                f"{self.repr_changes(changes, include_dependencies=True)}"
            )

    def assertOperationTypes(self, changes, app_label, position, types):
        if not changes.get(app_label):
            self.fail(f"No migrations found for {app_label}\n{self.repr_changes(changes)}")
        if len(changes[app_label]) < position + 1:
            self.fail(
                f"No migration at index {position} for {app_label}\n{self.repr_changes(changes)}"
            )
        migration = changes[app_label][position]
        real_types = [operation.__class__.__name__ for operation in migration.operations]
        if types != real_types:
            self.fail(
                f"Operation type mismatch for {app_label}.{migration.name} "
                f"(expected {types}):\n{self.repr_changes(changes)}"
            )

    def assertOperationAttributes(self, changes, app_label, position, operation_position, **attrs):
        if not changes.get(app_label):
            self.fail(f"No migrations found for {app_label}\n{self.repr_changes(changes)}")
        if len(changes[app_label]) < position + 1:
            self.fail(
                f"No migration at index {position} for {app_label}\n{self.repr_changes(changes)}"
            )
        migration = changes[app_label][position]
        if len(changes[app_label]) < position + 1:
            self.fail(
                f"No operation at index {operation_position} for "
                "{app_label}.{migration.name}\n{self.repr_changes(changes)}"
            )
        operation = migration.operations[operation_position]
        for attr, value in attrs.items():
            if getattr(operation, attr, None) != value:
                self.fail(
                    f"Attribute mismatch for {app_label}.{migration.name} op "
                    f"#{operation_position}, {attr} (expected  {value!r}, got "
                    f"{getattr(operation, attr, None)!r}):\n"
                    f"{self.repr_changes(changes)}"
                )

    def assertOperationFieldAttributes(
        self, changes, app_label, position, operation_position, **attrs
    ):
        if not changes.get(app_label):
            self.fail(f"No migrations found for {app_label}\n{self.repr_changes(changes)}")
        if len(changes[app_label]) < position + 1:
            self.fail(
                f"No migration at index {position} for {app_label}\n{self.repr_changes(changes)}"
            )
        migration = changes[app_label][position]
        if len(changes[app_label]) < position + 1:
            self.fail(
                f"No operation at index {operation_position} for "
                f"{app_label}.{migration.name}\n{self.repr_changes(changes)}"
            )
        operation = migration.operations[operation_position]
        if not hasattr(operation, "field"):
            self.fail(
                f"No field attribute for {app_label}.{migration.name} op #{{operation_position}}."
            )
        field = operation.field
        for attr, value in attrs.items():
            if getattr(field, attr, None) != value:
                self.fail(
                    f"Field attribute mismatch for {app_label}.{migration.name} "
                    f"op #{operation_position}, field.{attr} (expected {value!r}, "
                    f"got {getattr(field, attr, None)!r}):\n{self.repr_changes(changes)}"
                )

    def make_project_state(self, model_states):
        "Shortcut to make ProjectStates from lists of predefined models"
        project_state = ProjectState()
        for model_state in model_states:
            project_state.add_model(model_state.clone())
        return project_state

    def get_changes(self, before_states, after_states, questioner=None):
        if not isinstance(before_states, ProjectState):
            before_states = self.make_project_state(before_states)
        if not isinstance(after_states, ProjectState):
            after_states = self.make_project_state(after_states)
        return MigrationAutodetector(
            before_states,
            after_states,
            questioner,
        )._detect_changes()
