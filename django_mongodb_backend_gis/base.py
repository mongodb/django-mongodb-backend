from django_mongodb_backend.base import DatabaseWrapper as BaseDatabaseWrapper

from .features import DatabaseFeatures
from .operations import DatabaseOperations
from .schema import DatabaseSchemaEditor


class DatabaseWrapper(BaseDatabaseWrapper):
    SchemaEditorClass = DatabaseSchemaEditor
    features_class = DatabaseFeatures
    ops_class = DatabaseOperations
