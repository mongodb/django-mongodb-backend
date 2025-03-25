from itertools import chain

from django.core.exceptions import FieldDoesNotExist
from django.db import connections
from django.db.models import QuerySet
from django.db.models.query import RawModelIterable as BaseRawModelIterable
from django.db.models.query import RawQuerySet as BaseRawQuerySet
from django.db.models.sql.query import RawQuery as BaseRawQuery


class MongoQuerySet(QuerySet):
    def raw_aggregate(self, pipeline, using=None):
        return RawQuerySet(pipeline, model=self.model, using=using)


class RawQuerySet(BaseRawQuerySet):
    def __init__(self, pipeline, model=None, using=None):
        super().__init__(pipeline, model=model, using=using)
        self.query = RawQuery(pipeline, using=self.db, model=self.model)
        # Override the superclass's columns property which relies on PEP 249's
        # cursor.description. Instead, RawModelIterable will set the columns
        # based on the keys in the first result.
        self.columns = None

    def iterator(self):
        yield from RawModelIterable(self)


class RawQuery(BaseRawQuery):
    def __init__(self, pipeline, using, model):
        self.pipeline = pipeline
        super().__init__(sql=None, using=using)
        self.model = model

    def _execute_query(self):
        connection = connections[self.using]
        collection = connection.get_collection(self.model._meta.db_table)
        self.cursor = collection.aggregate(self.pipeline)

    def __str__(self):
        return str(self.pipeline)


class RawModelIterable(BaseRawModelIterable):
    def __iter__(self):
        """
        This is copied from the superclass except for the part that sets
        self.queryset.columns from the first result.
        """
        db = self.queryset.db
        query = self.queryset.query
        connection = connections[db]
        compiler = connection.ops.compiler("SQLCompiler")(query, connection, db)
        query_iterator = iter(query)
        try:
            # Get the columns for each result
            for result in query_iterator:
                # Associate fields to values
                self.queryset.columns = list(result.keys())
                # Use the new columns to define the new model_init_order.
                (
                    model_init_names,
                    model_init_pos,
                    annotation_fields,
                ) = self.queryset.resolve_model_init_order()
                model_cls = self.queryset.model
                if model_cls._meta.pk.attname not in model_init_names:
                    raise FieldDoesNotExist("Raw query must include the primary key")
                fields = [self.queryset.model_fields.get(c) for c in self.queryset.columns]
                converters = compiler.get_converters(
                    [f.get_col(f.model._meta.db_table) if f else None for f in fields]
                )
                # Make an iterator from the singular result
                result_iter = self._make_result([result])
                if converters:
                    result_iter = compiler.apply_converters(result_iter, converters)

                # Iterate once to generate a model object based solely on the result
                for values in result_iter:
                    model_init_values = [values[pos] for pos in model_init_pos]
                    instance = model_cls.from_db(db, model_init_names, model_init_values)
                    if annotation_fields:
                        for column, pos in annotation_fields:
                            setattr(instance, column, values[pos])
                    yield instance
        finally:
            query.cursor.close()

    def _make_result(self, query):
        """
        Convert documents (dictionaries) to tuples as expected by the rest
        of __iter__().
        """
        for result in query:
            # Create a tuple of values strictly from the outlined result columns
            yield tuple(result.get(key, None) for key in self.queryset.columns)
