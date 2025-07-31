from pymongo import GEOSPHERE
from pymongo.operations import IndexModel


class GISSchemaEditor:
    def _create_model_indexes(self, model, column_prefix="", parent_model=None):
        super()._create_model_indexes(model, column_prefix, parent_model)
        for field in model._meta.local_fields:
            if getattr(field, "spatial_index", False):
                self._add_spatial_index(parent_model or model, field, column_prefix)

    def add_field(self, model, field):
        super().add_field(model, field)
        if getattr(field, "spatial_index", False):
            self._add_spatial_index(model, field)

    def _alter_field(
        self,
        model,
        old_field,
        new_field,
        old_type,
        new_type,
        old_db_params,
        new_db_params,
        strict=False,
    ):
        super()._alter_field(
            model,
            old_field,
            new_field,
            old_type,
            new_type,
            old_db_params,
            new_db_params,
            strict=strict,
        )
        old_field_spatial_index = getattr(old_field, "spatial_index", False)
        new_field_spatial_index = getattr(new_field, "spatial_index", False)
        if not old_field_spatial_index and new_field_spatial_index:
            self._add_spatial_index(model, new_field)
        elif old_field_spatial_index and not new_field_spatial_index:
            self._delete_spatial_index(model, new_field)

    def remove_field(self, model, field):
        super().remove_field(model, field)
        if getattr(field, "spatial_index", False):
            self._delete_spatial_index(model, field)

    def _add_spatial_index(self, model, field, column_prefix=""):
        index_name = self._create_spatial_index_name(model, field, column_prefix)
        self.get_collection(model._meta.db_table).create_indexes(
            [IndexModel([(column_prefix + field.column, GEOSPHERE)], name=index_name)]
        )

    def _delete_spatial_index(self, model, field):
        index_name = self._create_spatial_index_name(model, field)
        self.get_collection(model._meta.db_table).drop_index(index_name)

    def _create_spatial_index_name(self, model, field, column_prefix=""):
        return f"{model._meta.db_table}_{column_prefix}{field.column}_id"
