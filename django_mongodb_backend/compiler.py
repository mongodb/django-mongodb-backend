import itertools
from collections import defaultdict

from bson import SON, json_util
from django.core.exceptions import EmptyResultSet, FieldError, FullResultSet
from django.db import IntegrityError, NotSupportedError
from django.db.models import Count
from django.db.models.aggregates import Aggregate, Variance
from django.db.models.expressions import Case, Col, OrderBy, Ref, Value, When
from django.db.models.functions.comparison import Coalesce
from django.db.models.functions.math import Power
from django.db.models.lookups import IsNull, Lookup
from django.db.models.sql import compiler
from django.db.models.sql.constants import GET_ITERATOR_CHUNK_SIZE, MULTI, SINGLE
from django.db.models.sql.datastructures import BaseTable
from django.db.models.sql.where import AND, WhereNode
from django.utils.functional import cached_property
from pymongo import ASCENDING, DESCENDING

from .expressions.search import SearchExpression, SearchVector
from .query import MongoQuery, wrap_database_errors
from .query_utils import is_direct_value


class SQLCompiler(compiler.SQLCompiler):
    """Base class for all Mongo compilers."""

    query_class = MongoQuery
    PARENT_FIELD_TEMPLATE = "parent__field__{}"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.aggregation_pipeline = None
        # Map columns to their subquery indices.
        self.column_indices = {}
        # A list of OrderBy objects for this query.
        self.order_by_objs = None
        self.subqueries = []
        # Atlas search stage.
        self.search_pipeline = []

    def _get_group_alias_column(self, expr, annotation_group_idx):
        """Generate a dummy field for use in the ids fields in $group."""
        replacement = None
        if isinstance(expr, Col):
            col = expr
        else:
            # If the column is a composite expression, create a field for it.
            alias = f"__annotation_group{next(annotation_group_idx)}"
            col = self._get_column_from_expression(expr, alias)
            replacement = col
        return col.target.column, replacement

    def _get_column_from_expression(self, expr, alias):
        """
        Create a column named `alias` from the given expression to hold the
        aggregate value.
        """
        column_target = expr.output_field.clone()
        column_target.db_column = alias
        column_target.set_attributes_from_name(alias)
        return Col(self.collection_name, column_target)

    def _get_replace_expr(self, sub_expr, group, alias):
        column_target = sub_expr.output_field.clone()
        column_target.db_column = alias
        column_target.set_attributes_from_name(alias)
        inner_column = Col(self.collection_name, column_target)
        if getattr(sub_expr, "distinct", False):
            # If the expression should return distinct values, use $addToSet to
            # deduplicate.
            rhs = sub_expr.as_mql(self, self.connection, resolve_inner_expression=True)
            group[alias] = {"$addToSet": rhs}
            replacing_expr = sub_expr.copy()
            replacing_expr.set_source_expressions([inner_column, None])
        else:
            group[alias] = sub_expr.as_mql(self, self.connection)
            replacing_expr = inner_column
        # Count must return 0 rather than null.
        if isinstance(sub_expr, Count):
            replacing_expr = Coalesce(replacing_expr, 0)
        # Variance = StdDev^2
        if isinstance(sub_expr, Variance):
            replacing_expr = Power(replacing_expr, 2)
        return replacing_expr

    def _prepare_expressions_for_pipeline(self, expression, target, annotation_group_idx):
        """
        Prepare expressions for the aggregation pipeline.

        Handle the computation of aggregation functions used by various
        expressions. Separate and create intermediate columns, and replace
        nodes to simulate a group by operation.

        MongoDB's $group stage doesn't allow operations over the aggregator,
        e.g. COALESCE(AVG(field), 3). However, it supports operations inside
        the aggregation, e.g. AVG(number * 2).

        Handle the first case by splitting the computation into stages: compute
        the aggregation first, then apply additional operations in a subsequent
        stage by replacing the aggregate expressions with new columns prefixed
        by `__aggregation`.
        """
        replacements = {}
        group = {}
        for sub_expr in self._get_aggregate_expressions(expression):
            alias = (
                f"__aggregation{next(annotation_group_idx)}" if sub_expr != expression else target
            )
            replacements[sub_expr] = self._get_replace_expr(sub_expr, group, alias)
        return replacements, group

    def _prepare_search_expressions_for_pipeline(self, expression, search_idx, replacements):
        """
        Collect and prepare unique search expressions for inclusion in an
        aggregation pipeline.

        Iterate over all search sub-expressions of the given expression.
        Assigning a unique alias to each and map them to their replacement
        expressions.
        """
        searches = {}
        for sub_expr in self._get_search_expressions(expression):
            if sub_expr not in replacements:
                alias = f"__search_expr.search{next(search_idx)}"
                replacements[sub_expr] = self._get_replace_expr(sub_expr, searches, alias)

    def _prepare_search_query_for_aggregation_pipeline(self, order_by):
        """
        Prepare expressions for the search pipeline.

        Handle the computation of search functions used by various expressions.
        Separate and create intermediate columns, and replace nodes to simulate
        a search operation.

        To apply operations over the $search or $searchVector stages, compute
        the $search or $vectorSearch first, then apply additional operations in
        a subsequent stage by replacing the aggregate expressions with a new
        document field prefixed by `__search_expr.search#`.
        """
        replacements = {}
        annotation_group_idx = itertools.count(start=1)
        for expr in self.query.annotation_select.values():
            self._prepare_search_expressions_for_pipeline(expr, annotation_group_idx, replacements)
        for expr, _ in order_by:
            self._prepare_search_expressions_for_pipeline(expr, annotation_group_idx, replacements)
        self._prepare_search_expressions_for_pipeline(
            self.having, annotation_group_idx, replacements
        )
        self._prepare_search_expressions_for_pipeline(
            self.get_where(), annotation_group_idx, replacements
        )
        return replacements

    def _prepare_annotations_for_aggregation_pipeline(self, order_by):
        """Prepare annotations for the aggregation pipeline."""
        replacements = {}
        group = {}
        annotation_group_idx = itertools.count(start=1)
        for target, expr in self.query.annotation_select.items():
            if expr.contains_aggregate:
                new_replacements, expr_group = self._prepare_expressions_for_pipeline(
                    expr, target, annotation_group_idx
                )
                replacements.update(new_replacements)
                group.update(expr_group)
        for expr, _ in order_by:
            if expr.contains_aggregate:
                new_replacements, expr_group = self._prepare_expressions_for_pipeline(
                    expr, None, annotation_group_idx
                )
                replacements.update(new_replacements)
                group.update(expr_group)
        having_replacements, having_group = self._prepare_expressions_for_pipeline(
            self.having, None, annotation_group_idx
        )
        replacements.update(having_replacements)
        group.update(having_group)
        return group, replacements

    def _get_group_expressions(self, order_by):
        if self.query.group_by is None:
            return []
        seen = set()
        expressions = set()
        if self.query.group_by is not True:
            # If group_by isn't True, then it's a list of expressions.
            for expr in self.query.group_by:
                if not hasattr(expr, "as_sql"):
                    expr = self.query.resolve_ref(expr)
                if isinstance(expr, Ref):
                    if expr.refs not in seen:
                        seen.add(expr.refs)
                        expressions.add(expr.source)
                else:
                    expressions.add(expr)
        for expr, _, alias in self.select:
            # Skip members that are already grouped.
            if alias not in seen:
                expressions |= set(expr.get_group_by_cols())
        if not self._meta_ordering:
            for expr, (_, _, is_ref) in order_by:
                # Skip references.
                if not is_ref:
                    expressions |= set(expr.get_group_by_cols())
        having_group_by = self.having.get_group_by_cols() if self.having else ()
        for expr in having_group_by:
            expressions.add(expr)
        return expressions

    def _get_group_id_expressions(self, order_by):
        """Generate group ID expressions for the aggregation pipeline."""
        replacements = {}
        group_expressions = self._get_group_expressions(order_by)
        if not group_expressions:
            ids = None
        else:
            annotation_group_idx = itertools.count(start=1)
            ids = {}
            columns = []
            for col in group_expressions:
                alias, replacement = self._get_group_alias_column(col, annotation_group_idx)
                columns.append((alias, col))
                if replacement is not None:
                    replacements[col] = replacement
                    if isinstance(col, Ref):
                        replacements[col.source] = replacement
            ids = self.get_project_fields(tuple(columns), force_expression=True)
        return ids, replacements

    def _build_aggregation_pipeline(self, ids, group):
        """Build the aggregation pipeline for grouping."""
        pipeline = []
        if not ids:
            group["_id"] = None
            pipeline.append({"$facet": {"group": [{"$group": group}]}})
            pipeline.append(
                {
                    "$addFields": {
                        key: {
                            "$getField": {
                                "input": {"$arrayElemAt": ["$group", 0]},
                                "field": key,
                            }
                        }
                        for key in group
                    }
                }
            )
        else:
            group["_id"] = ids
            pipeline.append({"$group": group})
            projected_fields = {key: f"$_id.{key}" for key in ids}
            pipeline.append({"$addFields": projected_fields})
            if "_id" not in projected_fields:
                pipeline.append({"$unset": "_id"})
        return pipeline

    def _compound_searches_queries(self, search_replacements):
        """
        Build a query pipeline from a mapping of search expressions to result
        columns.

        Currently only a single $search or $vectorSearch expression is
        supported. Combining multiple search expressions raises ValueError.

        This method will eventually support hybrid search by allowing the
        combination of $search and $vectorSearch operations.
        """
        if not search_replacements:
            return []
        if len(search_replacements) > 1:
            has_search = any(not isinstance(search, SearchVector) for search in search_replacements)
            has_vector_search = any(
                isinstance(search, SearchVector) for search in search_replacements
            )
            if has_search and has_vector_search:
                raise ValueError(
                    "Cannot combine a `$vectorSearch` with a `$search` operator. "
                    "If you need to combine them, consider restructuring your query logic or "
                    "running them as separate queries."
                )
            if has_vector_search:
                raise ValueError(
                    "Cannot combine two `$vectorSearch` operator. "
                    "If you need to combine them, consider restructuring your query logic or "
                    "running them as separate queries."
                )
            raise ValueError(
                "Only one $search operation is allowed per query. "
                f"Received {len(search_replacements)} search expressions. "
                "To combine multiple search expressions, use either a CompoundExpression for "
                "fine-grained control or CombinedSearchExpression for simple logical combinations."
            )
        pipeline = []
        for search, result_col in search_replacements.items():
            score_function = (
                "vectorSearchScore" if isinstance(search, SearchVector) else "searchScore"
            )
            pipeline.extend(
                [
                    search.as_mql(self, self.connection),
                    {
                        "$addFields": {
                            result_col.as_mql(self, self.connection, as_path=True): {
                                "$meta": score_function
                            }
                        }
                    },
                ]
            )
        return pipeline

    def pre_sql_setup(self, with_col_aliases=False):
        extra_select, order_by, group_by = super().pre_sql_setup(with_col_aliases=with_col_aliases)
        search_replacements = self._prepare_search_query_for_aggregation_pipeline(order_by)
        group, group_replacements = self._prepare_annotations_for_aggregation_pipeline(order_by)
        all_replacements = {**search_replacements, **group_replacements}
        self.search_pipeline = self._compound_searches_queries(search_replacements)
        # query.group_by is either:
        # - None: no GROUP BY
        # - True: group by select fields
        # - a list of expressions to group by.
        if group or self.query.group_by:
            ids, replacements = self._get_group_id_expressions(order_by)
            all_replacements.update(replacements)
            pipeline = self._build_aggregation_pipeline(ids, group)
            if self.having:
                having = self.having.replace_expressions(all_replacements).as_mql(
                    self, self.connection
                )
                # Add HAVING subqueries.
                for query in self.subqueries or ():
                    pipeline.extend(query.get_pipeline())
                # Remove the added subqueries.
                self.subqueries = []
                pipeline.append({"$match": {"$expr": having}})
            self.aggregation_pipeline = pipeline
        self.annotations = {
            target: expr.replace_expressions(all_replacements)
            for target, expr in self.query.annotation_select.items()
        }
        self.order_by_objs = [expr.replace_expressions(all_replacements) for expr, _ in order_by]
        if (where := self.get_where()) and search_replacements:
            self.set_where(where.replace_expressions(search_replacements))
        return extra_select, order_by, group_by

    def execute_sql(
        self, result_type=MULTI, chunked_fetch=False, chunk_size=GET_ITERATOR_CHUNK_SIZE
    ):
        self.pre_sql_setup()
        try:
            query = self.build_query(
                # Avoid $project (columns=None) if unneeded.
                self.columns
                if self.query.annotations or not self.query.default_cols or self.query.distinct
                else None
            )
        except EmptyResultSet:
            return iter([]) if result_type == MULTI else None

        cursor = query.get_cursor()
        if result_type == SINGLE:
            try:
                obj = cursor.next()
            except StopIteration:
                return None  # No result
            else:
                return self._make_result(obj, self.columns)
        # result_type is MULTI
        result = self.cursor_iter(cursor, chunk_size, self.columns)
        if not chunked_fetch:
            # If using non-chunked reads, read data into memory.
            return list(result)
        return result

    def results_iter(
        self,
        results=None,
        tuple_expected=False,
        chunked_fetch=False,
        chunk_size=GET_ITERATOR_CHUNK_SIZE,
    ):
        """
        Return an iterator over the results from executing query given
        to this compiler. Called by QuerySet methods.

        This method is copied from the superclass with one modification: the
        `if tuple_expected` block is deindented so that the result of
        _make_result() (a list) is cast to tuple as needed. For SQL database
        drivers, tuple results come from cursor.fetchmany(), so the cast is
        only needed there when apply_converters() casts the tuple to a list.
        This customized method could be removed if _make_result() cast its
        return value to a tuple, but that would be more expensive since that
        cast is not always needed.
        """
        if results is None:
            # QuerySet.values() or values_list()
            results = self.execute_sql(MULTI, chunked_fetch=chunked_fetch, chunk_size=chunk_size)

        fields = [s[0] for s in self.select[0 : self.col_count]]
        converters = self.get_converters(fields)
        rows = itertools.chain.from_iterable(results)
        if converters:
            rows = self.apply_converters(rows, converters)
        if tuple_expected:
            rows = map(tuple, rows)
        return rows

    def _make_result(self, entity, columns):
        """
        Decode values for the given fields from the database entity.

        The entity is assumed to be a dict using field database column
        names as keys.
        """
        result = []
        for name, col in columns:
            column_alias = getattr(col, "alias", None)
            obj = (
                # Use the related object...
                entity.get(column_alias, {})
                # ...if this column refers to an object for select_related().
                if column_alias is not None and column_alias != self.collection_name
                else entity
            )
            result.append(obj.get(name))
        return result

    def cursor_iter(self, cursor, chunk_size, columns):
        """Yield chunks of results from cursor."""
        chunk = []
        for row in cursor:
            chunk.append(self._make_result(row, columns))
            if len(chunk) == chunk_size:
                yield chunk
                chunk = []
        yield chunk

    def check_query(self):
        """Check if the current query is supported by the database."""
        if self.query.extra:
            if any(key.startswith("_prefetch_related_") for key in self.query.extra):
                raise NotSupportedError("QuerySet.prefetch_related() is not supported on MongoDB.")
            raise NotSupportedError("QuerySet.extra() is not supported on MongoDB.")

    def build_query(self, columns=None):
        """Check if the query is supported and prepare a MongoQuery."""
        self.check_query()
        query = self.query_class(self)
        ordering_fields, sort_ordering, extra_fields = self._get_ordering()
        query.ordering = sort_ordering
        if self.query.combinator:
            if not getattr(self.connection.features, f"supports_select_{self.query.combinator}"):
                raise NotSupportedError(
                    f"{self.query.combinator} is not supported on this database backend."
                )
            query.combinator_pipeline = self.get_combinator_queries()
        else:
            if self.query.distinct:
                # If query is distinct, build a $group stage for distinct
                # fields, then set project fields based on the grouped _id.
                distinct_fields = self.get_project_fields(
                    columns, ordering_fields, force_expression=True
                )
                if not query.aggregation_pipeline:
                    query.aggregation_pipeline = []
                query.aggregation_pipeline.extend(
                    [
                        {"$group": {"_id": distinct_fields}},
                        {"$project": {key: f"$_id.{key}" for key in distinct_fields}},
                    ]
                )
            else:
                # Otherwise, project fields without grouping.
                query.project_fields = self.get_project_fields(columns, ordering_fields)
            # If columns is None, then get_project_fields() won't add
            # ordering_fields to $project. Use $addFields (extra_fields) instead.
            if columns is None:
                extra_fields += ordering_fields
            query.lookup_pipeline = self.get_lookup_pipeline()
            where = self.get_where()
            try:
                expr = where.as_mql(self, self.connection) if where else {}
            except FullResultSet:
                query.match_mql = {}
            else:
                query.match_mql = {"$expr": expr}
        if extra_fields:
            query.extra_fields = self.get_project_fields(extra_fields, force_expression=True)
        query.subqueries = self.subqueries
        return query

    @cached_property
    def columns(self):
        """
        Return a tuple of (name, expression) with the columns and annotations
        which should be loaded by the query.
        """
        select_mask = self.query.get_select_mask()
        columns = (
            self.get_default_columns(select_mask) if self.query.default_cols else self.query.select
        )

        annotation_idx = 1

        def project_field(column):
            nonlocal annotation_idx
            if hasattr(column, "target"):
                # column is a Col.
                target = column.target.column
            # Handle Order By columns as refs columns.
            elif isinstance(column, OrderBy) and isinstance(column.expression, Ref):
                target = column.expression.refs
            else:
                # column is a Transform in values()/values_list() that needs a
                # name for $proj.
                target = f"__annotation{annotation_idx}"
                annotation_idx += 1
            return target, column

        selected = []
        if self.query.selected is None:
            selected = [
                *(project_field(col) for col in columns),
                *self.annotations.items(),
            ]
        else:
            for expression in self.query.selected.values():
                # Reference to an annotation.
                if isinstance(expression, str):
                    alias, expression = expression, self.annotations[expression]
                # Reference to a column.
                elif isinstance(expression, int):
                    alias, expression = project_field(columns[expression])
                selected.append((alias, expression))
        # Populate QuerySet.select_related() data.
        related_columns = []
        if self.query.select_related:
            self.get_related_selections(related_columns, select_mask)
            if related_columns:
                related_columns, _ = zip(*related_columns, strict=True)
        return tuple(selected) + tuple(map(project_field, related_columns))

    @cached_property
    def base_table(self):
        return next(
            (
                v
                for k, v in self.query.alias_map.items()
                if isinstance(v, BaseTable) and self.query.alias_refcount[k]
            ),
            None,
        )

    @cached_property
    def collection_name(self):
        if self.base_table:
            return self.base_table.table_alias or self.base_table.table_name
        # Use a dummy collection if the query doesn't specify a table.
        # For Constraint.validate():
        # SELECT 1 WHERE EXISTS(subquery checking if a constraint is violated)
        # is translated as:
        # [{"$facet": {"__null": []}},
        #  {"$lookup": {"the subquery"}},
        #  {"$match": {"condition to check from the subquery"}}]
        query = self.query_class(self)
        # The "__null" document is a placeholder so that the subquery has
        # somewhere to return its results.
        query.aggregation_pipeline = [{"$facet": {"__null": []}}]
        self.subqueries.insert(0, query)
        return "__null"

    @cached_property
    def collection(self):
        return self.connection.get_collection(self.collection_name)

    def get_combinator_queries(self):
        parts = []
        compilers = [
            query.get_compiler(self.using, self.connection, self.elide_empty)
            for query in self.query.combined_queries
        ]
        main_query_fields, _ = zip(*self.columns, strict=True)
        for compiler_ in compilers:
            try:
                # If the columns list is limited, then all combined queries
                # must have the same columns list. Set the selects defined on
                # the query on all combined queries, if not already set.
                selected = self.query.selected
                if selected is not None and compiler_.query.selected is None:
                    compiler_.query = compiler_.query.clone()
                    compiler_.query.set_values(selected)
                elif not compiler_.query.values_select and self.query.values_select:
                    compiler_.query = compiler_.query.clone()
                    compiler_.query.set_values(
                        (
                            *self.query.extra_select,
                            *self.query.values_select,
                            *self.query.annotation_select,
                        )
                    )
                compiler_.pre_sql_setup()
                compiler_.column_indices = self.column_indices
                columns = compiler_.columns
                parts.append((compiler_.build_query(columns), compiler_, columns))
            except EmptyResultSet:
                # Omit the empty queryset with UNION.
                if self.query.combinator == "union":
                    continue
                raise
        # Raise EmptyResultSet if all the combinator queries are empty.
        if not parts:
            raise EmptyResultSet
        # Make the combinator's stages.
        combinator_pipeline = None
        for part, compiler_, columns in parts:
            inner_pipeline = part.get_pipeline()
            # Standardize result fields.
            fields = {}
            # When a .count() is called, the main_query_field has length 1
            # otherwise it has the same length as columns.
            for alias, (ref, expr) in zip(main_query_fields, columns, strict=False):
                if isinstance(expr, Col) and expr.alias != compiler_.collection_name:
                    fields[expr.alias] = 1
                else:
                    fields[alias] = f"${ref}" if alias != ref else 1
            inner_pipeline.append({"$project": fields})
            # Combine query with the current combinator pipeline.
            if combinator_pipeline:
                combinator_pipeline.append(
                    {
                        "$unionWith": {
                            "coll": compiler_.base_table.table_name,
                            "pipeline": inner_pipeline,
                        }
                    }
                )
            else:
                combinator_pipeline = inner_pipeline
        if not self.query.combinator_all:
            ids = defaultdict(dict)
            for alias, expr in self.columns:
                # Unfold foreign fields.
                if isinstance(expr, Col) and expr.alias != self.collection_name:
                    ids[expr.alias][expr.target.column] = expr.as_mql(self, self.connection)
                else:
                    ids[alias] = f"${alias}"
            # Convert defaultdict to dict so it doesn't appear as
            # "defaultdict(<CLASS 'dict'>, ..." in query logging.
            ids = dict(ids)
            combinator_pipeline.append({"$group": {"_id": ids}})
            projected_fields = {key: f"$_id.{key}" for key in ids}
            combinator_pipeline.append({"$addFields": projected_fields})
            if "_id" not in projected_fields:
                combinator_pipeline.append({"$unset": "_id"})
        return combinator_pipeline

    def get_lookup_pipeline(self):
        result = []
        # To improve join performance, push conditions (filters) from the
        # WHERE ($match) clause to the JOIN ($lookup) clause.
        where = self.get_where()
        pushed_filters = defaultdict(list)
        for expr in where.children if where and where.connector == AND else ():
            # Push only basic lookups; no subqueries or complex conditions.
            # To avoid duplication across subqueries, only use the LHS target
            # table.
            if (
                isinstance(expr, Lookup)
                and isinstance(expr.lhs, Col)
                and (is_direct_value(expr.rhs) or isinstance(expr.rhs, Value | Col))
            ):
                pushed_filters[expr.lhs.alias].append(expr)
        for alias in tuple(self.query.alias_map):
            if not self.query.alias_refcount[alias] or self.collection_name == alias:
                continue
            result += self.query.alias_map[alias].as_mql(
                self, self.connection, WhereNode(pushed_filters[alias], connector=AND)
            )
        return result

    def _get_aggregate_expressions(self, expr):
        return self._get_all_expressions_of_type(expr, Aggregate)

    def _get_search_expressions(self, expr):
        return self._get_all_expressions_of_type(expr, SearchExpression)

    def _get_all_expressions_of_type(self, expr, target_type):
        stack = [expr]
        while stack:
            expr = stack.pop()
            if isinstance(expr, target_type):
                yield expr
            elif hasattr(expr, "get_source_expressions"):
                stack.extend(expr.get_source_expressions())

    def get_project_fields(self, columns=None, ordering=None, force_expression=False):
        if not columns:
            return {}
        fields = defaultdict(dict)
        for name, expr in columns + (ordering or ()):
            collection = expr.alias if isinstance(expr, Col) else None
            try:
                fields[collection][name] = (
                    1
                    # For brevity/simplicity, project {"field_name": 1}
                    # instead of {"field_name": "$field_name"}.
                    if isinstance(expr, Col) and name == expr.target.column and not force_expression
                    else expr.as_mql(self, self.connection)
                )
            except EmptyResultSet:
                empty_result_set_value = getattr(expr, "empty_result_set_value", NotImplemented)
                value = (
                    False if empty_result_set_value is NotImplemented else empty_result_set_value
                )
                fields[collection][name] = Value(value).as_mql(self, self.connection)
            except FullResultSet:
                fields[collection][name] = Value(True).as_mql(self, self.connection)
        # Annotations (stored in None) and the main collection's fields
        # should appear in the top-level of the fields dict.
        fields.update(fields.pop(None, {}))
        fields.update(fields.pop(self.collection_name, {}))
        # Convert defaultdict to dict so it doesn't appear as
        # "defaultdict(<CLASS 'dict'>, ..." in query logging.
        return dict(fields)

    def _get_ordering(self):
        """
        Process the query's OrderBy objects and return:
        - A tuple of ('field_name': Col/Expression, ...)
        - A bson.SON mapping to pass to $sort.
        - A tuple of ('field_name': Expression, ...) for expressions that need
          to be added to extra_fields.
        """
        fields = []
        sort_ordering = SON()
        extra_fields = []
        idx = itertools.count(start=1)
        for order in self.order_by_objs or []:
            if isinstance(order.expression, Col):
                field_name = order.as_mql(self, self.connection).removeprefix("$")
                fields.append((order.expression.target.column, order.expression))
            elif isinstance(order.expression, Ref):
                field_name = order.as_mql(self, self.connection).removeprefix("$")
            else:
                field_name = f"__order{next(idx)}"
                fields.append((field_name, order.expression))
            # If the expression is ordered by NULLS FIRST or NULLS LAST,
            # add a field for sorting that's 1 if null or 0 if not.
            if order.nulls_first or order.nulls_last:
                null_fieldname = f"__order{next(idx)}"
                condition = When(IsNull(order.expression, True), then=Value(1))
                extra_fields.append((null_fieldname, Case(condition, default=Value(0))))
                sort_ordering[null_fieldname] = DESCENDING if order.nulls_first else ASCENDING
            sort_ordering[field_name] = DESCENDING if order.descending else ASCENDING
        return tuple(fields), sort_ordering, tuple(extra_fields)

    def get_where(self):
        return getattr(self, "where", self.query.where)

    def set_where(self, value):
        self.where = value

    def explain_query(self):
        # Validate format (none supported) and options.
        options = self.connection.ops.explain_query_prefix(
            self.query.explain_info.format,
            **self.query.explain_info.options,
        )
        # Build the query pipeline.
        self.pre_sql_setup()
        query = self.build_query(
            # Avoid $project (columns=None) if unneeded.
            self.columns if self.query.annotations or not self.query.default_cols else None
        )
        pipeline = query.get_pipeline()
        # Explain the pipeline.
        kwargs = {}
        for option in self.connection.ops.explain_options:
            if value := options.get(option):
                kwargs[option] = value
        explain = self.connection.database.command(
            "explain",
            {"aggregate": self.collection_name, "pipeline": pipeline, "cursor": {}},
            **kwargs,
        )
        return [json_util.dumps(explain, indent=4, ensure_ascii=False)]


class SQLInsertCompiler(SQLCompiler):
    def execute_sql(self, returning_fields=None):
        self.pre_sql_setup()
        objs = []
        for obj in self.query.objs:
            field_values = {}
            for field in self.query.fields:
                value = field.get_db_prep_save(
                    getattr(obj, field.attname)
                    if self.query.raw
                    else field.pre_save(obj, obj._state.adding),
                    connection=self.connection,
                )
                if value is None and not field.null and not field.primary_key:
                    raise IntegrityError(
                        f"You can't set {field.name} (a non-nullable field) to None."
                    )

                field_values[field.column] = value
            objs.append(field_values)
        return self.insert(objs, returning_fields=returning_fields)

    @wrap_database_errors
    def insert(self, docs, returning_fields=None):
        """Store a list of documents using field columns as element names."""
        inserted_ids = self.collection.insert_many(
            docs, session=self.connection.session
        ).inserted_ids
        return [(x,) for x in inserted_ids] if returning_fields else []

    @cached_property
    def collection_name(self):
        return self.query.get_meta().db_table


class SQLDeleteCompiler(compiler.SQLDeleteCompiler, SQLCompiler):
    def execute_sql(self, result_type=MULTI):
        try:
            query = self.build_query()
        except EmptyResultSet:
            return 0
        else:
            return query.delete()

    def check_query(self):
        super().check_query()
        if not self.single_alias:
            raise NotSupportedError(
                "Cannot use QuerySet.delete() when querying across multiple collections on MongoDB."
            )

    def get_where(self):
        return self.query.where

    @cached_property
    def collection_name(self):
        return self.query.base_table


class SQLUpdateCompiler(compiler.SQLUpdateCompiler, SQLCompiler):
    def execute_sql(self, result_type):
        """
        Execute the specified update. Return the number of rows affected by
        the primary update query. The "primary update query" is the first
        non-empty query that is executed. Row counts for any subsequent,
        related queries are not available.
        """
        self.pre_sql_setup()
        values = {}
        for field, _, value in self.query.values:
            if hasattr(value, "resolve_expression"):
                value = value.resolve_expression(self.query, allow_joins=False, for_save=True)
                if value.contains_aggregate:
                    raise FieldError(
                        f"Aggregate functions are not allowed in this query ({field.name}={value})."
                    )
                if value.contains_over_clause:
                    raise FieldError(
                        f"Window expressions are not allowed in this query ({field.name}={value})."
                    )
            elif hasattr(value, "prepare_database_save"):
                if field.remote_field:
                    value = value.prepare_database_save(field)
                elif not getattr(field, "stores_model_instance", False):
                    raise TypeError(
                        f"Tried to update field {field} with a model "
                        f"instance, {value!r}. Use a value compatible with "
                        f"{field.__class__.__name__}."
                    )
            prepared = field.get_db_prep_save(value, connection=self.connection)
            if hasattr(value, "as_mql"):
                prepared = prepared.as_mql(self, self.connection)
            values[field.column] = prepared
        try:
            criteria = self.build_query().match_mql
        except EmptyResultSet:
            return 0
        is_empty = not bool(values)
        rows = 0 if is_empty else self.update(criteria, [{"$set": values}])
        for query in self.query.get_related_updates():
            aux_rows = query.get_compiler(self.using).execute_sql(result_type)
            if is_empty and aux_rows:
                rows = aux_rows
                is_empty = False
        return rows

    @wrap_database_errors
    def update(self, criteria, pipeline):
        return self.collection.update_many(
            criteria, pipeline, session=self.connection.session
        ).matched_count

    def check_query(self):
        super().check_query()
        if len([a for a in self.query.alias_map if self.query.alias_refcount[a]]) > 1:
            raise NotSupportedError(
                "Cannot use QuerySet.update() when querying across multiple collections on MongoDB."
            )

    def get_where(self):
        return self.query.where

    @cached_property
    def collection_name(self):
        return self.query.base_table


class SQLAggregateCompiler(SQLCompiler):
    def build_query(self, columns=None):
        query = self.query_class(self)
        query.project_fields = self.get_project_fields(tuple(self.annotations.items()))
        compiler = self.query.inner_query.get_compiler(
            self.using,
            elide_empty=self.elide_empty,
        )
        compiler.pre_sql_setup(with_col_aliases=False)
        # Avoid $project (columns=None) if unneeded.
        columns = (
            compiler.columns
            if self.query.annotations or not self.query.default_cols or self.query.distinct
            else None
        )
        subquery = compiler.build_query(columns)
        query.subqueries = [subquery]
        return query

    def _make_result(self, result, columns=None):
        return [result[k] for k in self.query.annotation_select]
