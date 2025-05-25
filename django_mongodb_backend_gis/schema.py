from django.contrib.gis.db.models import GeometryField
from pymongo import GEOSPHERE
from pymongo.operations import IndexModel

from django_mongodb_backend.schema import DatabaseSchemaEditor as BaseSchemaEditor


class DatabaseSchemaEditor(BaseSchemaEditor):
    def _field_should_be_indexed(self, model, field):
        if getattr(field, "spatial_index", False):
            return True
        return super()._field_should_be_indexed(model, field)

    def _add_field_index(self, model, field, *, column_prefix=""):
        if hasattr(field, "geodetic"):
            self._add_spatial_index(model, field)
        else:
            super()._add_field_index(model, field, column_prefix=column_prefix)

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

        old_field_spatial_index = isinstance(old_field, GeometryField) and old_field.spatial_index
        new_field_spatial_index = isinstance(new_field, GeometryField) and new_field.spatial_index
        if not old_field_spatial_index and new_field_spatial_index:
            self._add_spatial_index(model, new_field)
        elif old_field_spatial_index and not new_field_spatial_index:
            self._delete_spatial_index(model, new_field)

    def _add_spatial_index(self, model, field):
        index_name = self._create_spatial_index_name(model, field)
        self.get_collection(model._meta.db_table).create_indexes(
            [
                IndexModel(
                    [
                        (field.column, GEOSPHERE),
                    ],
                    name=index_name,
                )
            ]
        )

    def _delete_spatial_index(self, model, field):
        index_name = self._create_spatial_index_name(model, field)
        self.get_collection(model._meta.db_table).drop_index(index_name)

    def _create_spatial_index_name(self, model, field):
        return f"{model._meta.db_table}_{field.column}_id"
