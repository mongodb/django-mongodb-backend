from django.db.migrations import operations
from django.db.migrations.autodetector import (
    MigrationAutodetector as BaseMigrationAutodetector,
)
from django.db.migrations.autodetector import OperationDependency
from django.db.migrations.utils import resolve_relation


class MigrationAutodetector(BaseMigrationAutodetector):
    def generate_renamed_models(self):
        # Treat unmanaged models like managed models so that all migration
        # operations are generated for them, not just CreateModel/DeleteModel.
        # Obsolete once https://code.djangoproject.com/ticket/35813 is fixed.
        self.old_model_keys |= self.old_unmanaged_keys
        self.old_unmanaged_keys = set()
        self.new_model_keys |= self.new_unmanaged_keys
        self.new_unmanaged_keys = set()
        super().generate_renamed_models()

    def add_operation(self, app_label, operation, dependencies=None, beginning=False):
        # Unlike relational fields, embedded model fields don't get a
        # dependency on the referenced model's creation, since they have no
        # remote_field. Add a dependency on the CreateModel of any embedded
        # models so they are created first, whether the embedding field is part
        # of a CreateModel (e.g. an initial migration) or an AddField /
        # AlterField (e.g. adding an embedded field to an existing model).
        # Otherwise the string references that EmbeddedModelField.deconstruct()
        # serializes can't be resolved while a partial migration state is
        # rendered (the embedded model wouldn't exist in the state yet).
        if isinstance(operation, operations.CreateModel):
            model_name = operation.name_lower
            fields = (field for _, field in operation.fields)
        elif isinstance(operation, (operations.AddField, operations.AlterField)):
            model_name = operation.model_name_lower
            fields = [operation.field]
        else:
            fields = None
        if fields is not None:
            dependencies = list(dependencies or [])
            for field in fields:
                for embedded_model in self._get_embedded_models(field):
                    dependency = resolve_relation(embedded_model, app_label, model_name)
                    dependencies.append(
                        OperationDependency(*dependency, None, OperationDependency.Type.CREATE)
                    )
        super().add_operation(app_label, operation, dependencies=dependencies, beginning=beginning)

    @staticmethod
    def _get_embedded_models(field):
        """Yield the model(s) referenced by an embedded model field, if any."""
        if (embedded_model := getattr(field, "embedded_model", None)) is not None:
            yield embedded_model
        yield from getattr(field, "embedded_models", None) or ()
