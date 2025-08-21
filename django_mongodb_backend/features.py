from django.core.exceptions import ImproperlyConfigured
from django.db.backends.base.features import BaseDatabaseFeatures
from django.utils.functional import cached_property
from pymongo.errors import OperationFailure

try:
    from .gis.features import GISFeatures
except ImproperlyConfigured:
    # GIS libraries (GDAL/GEOS) not installed.
    class GISFeatures:
        pass


class DatabaseFeatures(GISFeatures, BaseDatabaseFeatures):
    minimum_database_version = (6, 0)
    allow_sliced_subqueries_with_in = False
    allows_multiple_constraints_on_same_fields = False
    can_create_inline_fk = False
    can_introspect_foreign_keys = False
    can_return_rows_from_bulk_insert = True
    greatest_least_ignores_nulls = True
    has_json_object_function = False
    has_native_json_field = True
    rounds_to_even = True
    supports_boolean_expr_in_select_clause = True
    supports_collation_on_charfield = False
    supports_column_check_constraints = False
    supports_date_lookup_using_string = False
    supports_deferrable_unique_constraints = False
    supports_explaining_query_execution = True
    supports_expression_defaults = False
    supports_expression_indexes = False
    supports_foreign_keys = False
    supports_ignore_conflicts = False
    supports_json_field_contains = False
    # BSON Date type doesn't support microsecond precision.
    supports_microsecond_precision = False
    supports_paramstyle_pyformat = False
    supports_select_difference = False
    supports_select_intersection = False
    supports_sequence_reset = False
    supports_slicing_ordering_in_compound = True
    supports_table_check_constraints = False
    supports_temporal_subtraction = True
    # MongoDB stores datetimes in UTC.
    supports_timezones = False
    # While MongoDB supports transactions in some configurations (see
    # DatabaseFeatures._supports_transactions), django.db.transaction.atomic() is a
    # no-op on this backend.
    supports_transactions = False
    supports_unspecified_pk = True
    uses_savepoints = False

    _django_test_expected_failures = {
        # $concat only supports strings, not int
        "db_functions.text.test_concat.ConcatTests.test_concat_non_str",
        # QuerySet.order_by() with annotation transform doesn't work:
        # "Expression $mod takes exactly 2 arguments. 1 were passed in"
        # https://github.com/django/django/commit/b0ad41198b3e333f57351e3fce5a1fb47f23f376
        "aggregation.tests.AggregateTestCase.test_order_by_aggregate_transform",
        # 'NulledTransform' object has no attribute 'as_mql'.
        "lookup.tests.LookupTests.test_exact_none_transform",
        # BaseExpression.convert_value() crashes with Decimal128.
        "aggregation.tests.AggregateTestCase.test_combine_different_types",
        "annotations.tests.NonAggregateAnnotationTestCase.test_combined_f_expression_annotation_with_aggregation",
        # Pattern lookups that use regexMatch don't work on JSONField:
        # Unsupported conversion from array to string in $convert
        "model_fields.test_jsonfield.TestQuerying.test_icontains",
        # Unexpected alias_refcount in alias_map.
        "queries.tests.Queries1Tests.test_order_by_tables",
        # Pattern lookups (startswith, regex, etc.) don't work on non-string
        # fields: https://jira.mongodb.org/browse/INTPYTHON-734
        "admin_changelist.tests.ChangeListTests.test_pk_in_search_fields",
        "admin_changelist.tests.ChangeListTests.test_related_field_multiple_search_terms",
        "lookup.tests.LookupTests.test_lookup_int_as_str",
        "lookup.tests.LookupTests.test_regex_non_string",
        # The $sum aggregation returns 0 instead of None for null.
        "aggregation.test_filter_argument.FilteredAggregateTests.test_plain_annotate",
        "aggregation.tests.AggregateTestCase.test_aggregation_default_passed_another_aggregate",
        "aggregation.tests.AggregateTestCase.test_annotation_expressions",
        "aggregation.tests.AggregateTestCase.test_reverse_fkey_annotate",
        "aggregation_regress.tests.AggregationTests.test_annotation_disjunction",
        "aggregation_regress.tests.AggregationTests.test_decimal_aggregate_annotation_filter",
        # subclasses of BaseDatabaseWrapper may require an is_usable() method
        "backends.tests.BackendTestCase.test_is_usable_after_database_disconnects",
        # Connection creation doesn't follow the usual Django API.
        "backends.tests.ThreadTests.test_pass_connection_between_threads",
        "backends.tests.ThreadTests.test_default_connection_thread_local",
        # Object of type ObjectId is not JSON serializable.
        "auth_tests.test_views.LoginTest.test_login_session_without_hash_session_key",
        # GenericRelation.value_to_string() assumes integer pk.
        "contenttypes_tests.test_fields.GenericRelationTests.test_value_to_string",
        # icontains doesn't work on ArrayField:
        # Unsupported conversion from array to string in $convert
        "model_fields_.test_arrayfield.QueryingTests.test_icontains",
        # ArrayField's contained_by lookup crashes with Exists: "both operands "
        # of $setIsSubset must be arrays. Second argument is of type: null"
        # https://jira.mongodb.org/browse/SERVER-99186
        "model_fields_.test_arrayfield.QueryingTests.test_contained_by_subquery",
        # Value.as_mql() doesn't call output_field.get_db_prep_save():
        # https://github.com/mongodb/django-mongodb-backend/issues/282
        "model_fields.test_jsonfield.TestSaveLoad.test_bulk_update_custom_get_prep_value",
        # To debug: https://github.com/mongodb/django-mongodb-backend/issues/362
        "constraints.tests.UniqueConstraintTests.test_validate_case_when",
    }
    # $bitAnd, #bitOr, and $bitXor are new in MongoDB 6.3.
    _django_test_expected_failures_bitwise = {
        "expressions.tests.ExpressionOperatorTests.test_lefthand_bitwise_and",
        "expressions.tests.ExpressionOperatorTests.test_lefthand_bitwise_or",
        "expressions.tests.ExpressionOperatorTests.test_lefthand_bitwise_xor",
        "expressions.tests.ExpressionOperatorTests.test_lefthand_bitwise_xor_null",
        "expressions.tests.ExpressionOperatorTests.test_lefthand_bitwise_xor_right_null",
        "expressions.tests.ExpressionOperatorTests.test_lefthand_transformed_field_bitwise_or",
    }

    @cached_property
    def django_test_expected_failures(self):
        expected_failures = super().django_test_expected_failures
        expected_failures.update(self._django_test_expected_failures)
        if not self.is_mongodb_6_3:
            expected_failures.update(self._django_test_expected_failures_bitwise)
        return expected_failures

    _django_test_skips = {
        "Database defaults aren't supported by MongoDB.": {
            # bson.errors.InvalidDocument: cannot encode object:
            # <django.db.models.expressions.DatabaseDefault
            "basic.tests.ModelInstanceCreationTests.test_save_primary_with_db_default",
            "basic.tests.ModelInstanceCreationTests.test_save_primary_with_falsey_db_default",
            "constraints.tests.UniqueConstraintTests.test_database_default",
            "field_defaults.tests.DefaultTests",
            "migrations.test_operations.OperationTests.test_add_field_both_defaults",
            "migrations.test_operations.OperationTests.test_add_field_database_default",
            "migrations.test_operations.OperationTests.test_add_field_database_default_special_char_escaping",
            "migrations.test_operations.OperationTests.test_alter_field_add_database_default",
            "migrations.test_operations.OperationTests.test_alter_field_change_blank_nullable_database_default_to_not_null",
            "migrations.test_operations.OperationTests.test_alter_field_change_default_to_database_default",
            "migrations.test_operations.OperationTests.test_alter_field_change_nullable_to_database_default_not_null",
            "migrations.test_operations.OperationTests.test_alter_field_change_nullable_to_decimal_database_default_not_null",
            "schema.tests.SchemaTests.test_db_default_output_field_resolving",
            "schema.tests.SchemaTests.test_rename_keep_db_default",
            "validation.test_unique.PerformUniqueChecksTest.test_unique_db_default",
        },
        "Insert expressions aren't supported.": {
            "bulk_create.tests.BulkCreateTests.test_bulk_insert_now",
            "bulk_create.tests.BulkCreateTests.test_bulk_insert_expressions",
            "expressions.tests.BasicExpressionsTests.test_new_object_create",
            "expressions.tests.BasicExpressionsTests.test_new_object_save",
            "expressions.tests.BasicExpressionsTests.test_object_create_with_aggregate",
            "expressions.tests.BasicExpressionsTests.test_object_create_with_f_expression_in_subquery",
            "expressions.tests.BasicExpressionsTests.test_object_update_unsaved_objects",
            # PI()
            "db_functions.math.test_round.RoundTests.test_decimal_with_precision",
            "db_functions.math.test_round.RoundTests.test_float_with_precision",
        },
        "Check constraints are not supported.": {
            # Constraint.validate() crashes:
            # AttributeError: 'NoneType' object has no attribute 'db_table'
            "constraints.tests.CheckConstraintTests.test_database_default",
            "constraints.tests.CheckConstraintTests.test_validate",
            "constraints.tests.CheckConstraintTests.test_validate_boolean_expressions",
            "constraints.tests.CheckConstraintTests.test_validate_custom_error",
            "constraints.tests.CheckConstraintTests.test_validate_jsonfield_exact",
            "constraints.tests.CheckConstraintTests.test_validate_nullable_field_with_none",
            "constraints.tests.CheckConstraintTests.test_validate_nullable_jsonfield",
            "constraints.tests.CheckConstraintTests.test_validate_pk_field",
            "constraints.tests.CheckConstraintTests.test_validate_rawsql_expressions_noop",
        },
        "MongoDB doesn't rename an index when a field is renamed.": {
            "migrations.test_operations.OperationTests.test_rename_field_index_together",
            "migrations.test_operations.OperationTests.test_rename_field_unique_together",
        },
        "Pattern lookups on UUIDField are not supported.": {
            "model_fields.test_uuid.TestQuerying.test_contains",
            "model_fields.test_uuid.TestQuerying.test_endswith",
            "model_fields.test_uuid.TestQuerying.test_filter_with_expr",
            "model_fields.test_uuid.TestQuerying.test_icontains",
            "model_fields.test_uuid.TestQuerying.test_iendswith",
            "model_fields.test_uuid.TestQuerying.test_iexact",
            "model_fields.test_uuid.TestQuerying.test_istartswith",
            "model_fields.test_uuid.TestQuerying.test_startswith",
        },
        "QuerySet.prefetch_related() is not supported on MongoDB.": {
            "backends.base.test_creation.TestDeserializeDbFromString.test_serialize_db_to_string_base_manager_with_prefetch_related",
            "fixtures.tests.FixtureLoadingTests.test_dumpdata_objects_with_prefetch_related",
            "fixtures.tests.FixtureLoadingTests.test_loading_and_dumping",
            "m2m_through_regress.test_multitable.MultiTableTests.test_m2m_prefetch_proxied",
            "m2m_through_regress.test_multitable.MultiTableTests.test_m2m_prefetch_reverse_proxied",
            "many_to_many.tests.ManyToManyQueryTests.test_prefetch_related_no_queries_optimization_disabled",
            "many_to_many.tests.ManyToManyTests.test_add_after_prefetch",
            "many_to_many.tests.ManyToManyTests.test_add_then_remove_after_prefetch",
            "many_to_many.tests.ManyToManyTests.test_clear_after_prefetch",
            "many_to_many.tests.ManyToManyTests.test_create_after_prefetch",
            "many_to_many.tests.ManyToManyTests.test_remove_after_prefetch",
            "many_to_many.tests.ManyToManyTests.test_set_after_prefetch",
            "model_forms.tests.OtherModelFormTests.test_prefetch_related_queryset",
            "prefetch_related.test_prefetch_related_objects.PrefetchRelatedObjectsTests",
            "prefetch_related.test_uuid.UUIDPrefetchRelated",
            "prefetch_related.test_uuid.UUIDPrefetchRelatedLookups",
            "prefetch_related.tests.CustomPrefetchTests",
            "prefetch_related.tests.DefaultManagerTests.test_m2m_then_m2m",
            "prefetch_related.tests.ForeignKeyToFieldTest",
            "prefetch_related.tests.GenericRelationTests.test_traverse_GFK",
            "prefetch_related.tests.LookupOrderingTest.test_order",
            "prefetch_related.tests.MultiDbTests.test_using_is_honored_m2m",
            "prefetch_related.tests.MultiTableInheritanceTest",
            "prefetch_related.tests.PrefetchRelatedTests",
            "prefetch_related.tests.ReadPrefetchedObjectsCacheTests",
            "prefetch_related.tests.Ticket21410Tests",
            "queryset_pickle.tests.PickleabilityTestCase.test_pickle_prefetch_related_with_m2m_and_objects_deletion",
            "serializers.test_json.JsonSerializerTestCase.test_serialize_prefetch_related_m2m",
            "serializers.test_json.JsonSerializerTestCase.test_serialize_prefetch_related_m2m_with_natural_keys",
            "serializers.test_jsonl.JsonlSerializerTestCase.test_serialize_prefetch_related_m2m",
            "serializers.test_jsonl.JsonlSerializerTestCase.test_serialize_prefetch_related_m2m_with_natural_keys",
            "serializers.test_xml.XmlSerializerTestCase.test_serialize_prefetch_related_m2m",
            "serializers.test_xml.XmlSerializerTestCase.test_serialize_prefetch_related_m2m_with_natural_keys",
            "serializers.test_yaml.YamlSerializerTestCase.test_serialize_prefetch_related_m2m",
            "serializers.test_yaml.YamlSerializerTestCase.test_serialize_prefetch_related_m2m_with_natural_keys",
        },
        "AutoField not supported.": {
            "bulk_create.tests.BulkCreateTests.test_bulk_insert_nullable_fields",
            "introspection.tests.IntrospectionTests.test_sequence_list",
            "lookup.tests.LookupTests.test_filter_by_reverse_related_field_transform",
            "lookup.tests.LookupTests.test_in_ignore_none_with_unhashable_items",
            "m2m_through_regress.tests.ThroughLoadDataTestCase.test_sequence_creation",
            "many_to_many.tests.ManyToManyTests.test_add_remove_invalid_type",
            "many_to_one.tests.ManyToOneTests.test_fk_to_smallautofield",
            "many_to_one.tests.ManyToOneTests.test_fk_to_bigautofield",
            "migrations.test_operations.OperationTests.test_autofield__bigautofield_foreignfield_growth",
            "migrations.test_operations.OperationTests.test_model_with_bigautofield",
            "migrations.test_operations.OperationTests.test_smallfield_autofield_foreignfield_growth",
            "migrations.test_operations.OperationTests.test_smallfield_bigautofield_foreignfield_growth",
            "model_fields.test_autofield.AutoFieldTests",
            "model_fields.test_autofield.BigAutoFieldTests",
            "model_fields.test_autofield.SmallAutoFieldTests",
            "queries.tests.TestInvalidValuesRelation.test_invalid_values",
            "schema.tests.SchemaTests.test_alter_autofield_pk_to_bigautofield_pk",
            "schema.tests.SchemaTests.test_alter_autofield_pk_to_smallautofield_pk",
        },
        "Converters aren't run on returning fields from insert.": {
            # Unsure this is needed for this backend. Can implement by request.
            # https://github.com/django/django/commit/d9de74141e8a920940f1b91ed0a3ccb835b55729
            "custom_pk.tests.CustomPKTests.test_auto_field_subclass_bulk_create",
            "custom_pk.tests.CustomPKTests.test_auto_field_subclass_create",
        },
        "MongoDB does not enforce PositiveIntegerField constraint.": {
            "model_fields.test_integerfield.PositiveIntegerFieldTests.test_negative_values",
        },
        "Test assumes integer primary key.": {
            "custom_managers.tests.CustomManagersRegressTestCase.test_save_clears_annotations_from_base_manager",
            "db_functions.comparison.test_cast.CastTests.test_cast_to_integer_foreign_key",
            "expressions.tests.BasicExpressionsTests.test_nested_subquery_outer_ref_with_autofield",
            "model_fields.test_foreignkey.ForeignKeyTests.test_to_python",
            "queries.test_qs_combinators.QuerySetSetOperationTests.test_order_raises_on_non_selected_column",
            "queries.tests.RelatedLookupTypeTests.test_values_queryset_lookup",
            "queries.tests.ValuesSubqueryTests.test_values_in_subquery",
            "sites_tests.tests.CreateDefaultSiteTests.test_no_site_id",
        },
        "Cannot use QuerySet.delete() when querying across multiple collections on MongoDB.": {
            "admin_changelist.tests.ChangeListTests.test_distinct_for_many_to_many_at_second_level_in_search_fields",
            "admin_changelist.tests.ChangeListTests.test_distinct_for_through_m2m_at_second_level_in_list_filter",
            "delete.tests.FastDeleteTests.test_fast_delete_aggregation",
            "delete.tests.FastDeleteTests.test_fast_delete_empty_no_update_can_self_select",
            "delete.tests.FastDeleteTests.test_fast_delete_full_match",
            "delete.tests.FastDeleteTests.test_fast_delete_joined_qs",
            "delete_regress.tests.DeleteTests.test_meta_ordered_delete",
            "delete_regress.tests.Ticket19102Tests.test_ticket_19102_annotate",
            "delete_regress.tests.Ticket19102Tests.test_ticket_19102_defer",
            "delete_regress.tests.Ticket19102Tests.test_ticket_19102_select_related",
            "one_to_one.tests.OneToOneTests.test_o2o_primary_key_delete",
        },
        "Cannot use QuerySet.delete() when a subquery is required.": {
            "custom_managers.tests.CustomManagerTests.test_removal_through_default_m2m_related_manager",
            "custom_managers.tests.CustomManagerTests.test_removal_through_specified_m2m_related_manager",
            "delete_regress.tests.DeleteTests.test_self_reference_with_through_m2m_at_second_level",
            "many_to_many.tests.ManyToManyTests.test_assign",
            "many_to_many.tests.ManyToManyTests.test_assign_ids",
            "many_to_many.tests.ManyToManyTests.test_clear",
            "many_to_many.tests.ManyToManyTests.test_remove",
            "many_to_many.tests.ManyToManyTests.test_reverse_assign_with_queryset",
            "many_to_many.tests.ManyToManyTests.test_set",
            "many_to_many.tests.ManyToManyTests.test_set_existing_different_type",
        },
        "Cannot use QuerySet.update() when querying across multiple collections on MongoDB.": {
            "custom_managers.tests.CustomManagersRegressTestCase.test_refresh_from_db_when_default_manager_filters",
            "expressions.tests.BasicExpressionsTests.test_filter_with_join",
            "model_inheritance.tests.ModelInheritanceDataTests.test_update_works_on_parent_and_child_models_at_once",
            "queries.tests.Queries4Tests.test_ticket7095",
            "queries.tests.Queries5Tests.test_ticket9848",
            "update.tests.AdvancedTests.test_update_annotated_multi_table_queryset",
            "update.tests.AdvancedTests.test_update_ordered_by_m2m_annotation",
            "update.tests.AdvancedTests.test_update_ordered_by_m2m_annotation_desc",
            "update.tests.AdvancedTests.test_update_values_annotation",
        },
        "QuerySet.extra() is not supported.": {
            "aggregation.tests.AggregateTestCase.test_exists_extra_where_with_aggregate",
            "annotations.tests.NonAggregateAnnotationTestCase.test_column_field_ordering",
            "annotations.tests.NonAggregateAnnotationTestCase.test_column_field_ordering_with_deferred",
            "basic.tests.ModelTest.test_extra_method_select_argument_with_dashes",
            "basic.tests.ModelTest.test_extra_method_select_argument_with_dashes_and_values",
            "defer.tests.DeferTests.test_defer_extra",
            "delete_regress.tests.Ticket19102Tests.test_ticket_19102_extra",
            "extra_regress.tests.ExtraRegressTests",
            "lookup.tests.LookupTests.test_values",
            "lookup.tests.LookupTests.test_values_list",
            "many_to_one.tests.ManyToOneTests.test_selects",
            "ordering.tests.OrderingTests.test_extra_ordering",
            "ordering.tests.OrderingTests.test_extra_ordering_quoting",
            "ordering.tests.OrderingTests.test_extra_ordering_with_table_name",
            "queries.test_qs_combinators.QuerySetSetOperationTests.test_union_multiple_models_with_values_list_and_order_by_extra_select",
            "queries.test_qs_combinators.QuerySetSetOperationTests.test_union_with_extra_and_values_list",
            "queries.tests.EscapingTests.test_ticket_7302",
            "queries.tests.Queries1Tests.test_tickets_1878_2939",
            "queries.tests.Queries1Tests.test_tickets_7087_12242",
            "queries.tests.Queries5Tests.test_extra_select_literal_percent_s",
            "queries.tests.Queries5Tests.test_ticket7256",
            "queries.tests.ValuesQuerysetTests.test_extra_multiple_select_params_values_order_by",
            "queries.tests.ValuesQuerysetTests.test_extra_select_params_values_order_in_extra",
            "queries.tests.ValuesQuerysetTests.test_extra_values",
            "queries.tests.ValuesQuerysetTests.test_extra_values_list",
            "queries.tests.ValuesQuerysetTests.test_extra_values_order_multiple",
            "queries.tests.ValuesQuerysetTests.test_extra_values_order_twice",
            "queries.tests.ValuesQuerysetTests.test_flat_extra_values_list",
            "queries.tests.ValuesQuerysetTests.test_named_values_list_with_fields",
            "queries.tests.ValuesQuerysetTests.test_named_values_list_without_fields",
            "select_related.tests.SelectRelatedTests.test_select_related_with_extra",
        },
        "Test inspects query for SQL": {
            "aggregation.tests.AggregateAnnotationPruningTests.test_non_aggregate_annotation_pruned",
            "aggregation.tests.AggregateAnnotationPruningTests.test_unreferenced_aggregate_annotation_pruned",
            "aggregation.tests.AggregateAnnotationPruningTests.test_unused_aliased_aggregate_pruned",
            "aggregation.tests.AggregateAnnotationPruningTests.test_referenced_aggregate_annotation_kept",
            "aggregation.tests.AggregateTestCase.test_count_star",
            "delete.tests.DeletionTests.test_only_referenced_fields_selected",
            "expressions.tests.ExistsTests.test_optimizations",
            "lookup.tests.LookupTests.test_in_ignore_none",
            "lookup.tests.LookupTests.test_lookup_direct_value_rhs_unwrapped",
            "lookup.tests.LookupTests.test_textfield_exact_null",
            "many_to_many.tests.ManyToManyQueryTests.test_count_join_optimization_disabled",
            "many_to_many.tests.ManyToManyQueryTests.test_exists_join_optimization_disabled",
            "many_to_many.tests.ManyToManyTests.test_custom_default_manager_exists_count",
            "migrations.test_commands.MigrateTests.test_migrate_syncdb_app_label",
            "migrations.test_commands.MigrateTests.test_migrate_syncdb_deferred_sql_executed_with_schemaeditor",
            "queries.tests.ExistsSql.test_exists",
            "queries.tests.Queries6Tests.test_col_alias_quoted",
            "schema.tests.SchemaTests.test_rename_column_renames_deferred_sql_references",
            "schema.tests.SchemaTests.test_rename_table_renames_deferred_sql_references",
        },
        "Test executes raw SQL.": {
            "aggregation.tests.AggregateTestCase.test_coalesced_empty_result_set",
            "aggregation_regress.tests.AggregationTests.test_annotate_with_extra",
            "aggregation_regress.tests.AggregationTests.test_annotation",
            "aggregation_regress.tests.AggregationTests.test_more_more3",
            "aggregation_regress.tests.AggregationTests.test_more_more_more3",
            "annotations.tests.NonAggregateAnnotationTestCase.test_raw_sql_with_inherited_field",
            "async.test_async_queryset.AsyncQuerySetTest.test_raw",
            "backends.base.test_base.ExecuteWrapperTests",
            "backends.tests.BackendTestCase.test_cursor_contextmanager",
            "backends.tests.BackendTestCase.test_cursor_executemany",
            "backends.tests.BackendTestCase.test_cursor_executemany_with_empty_params_list",
            "backends.tests.BackendTestCase.test_cursor_executemany_with_iterator",
            "backends.tests.BackendTestCase.test_duplicate_table_error",
            "backends.tests.BackendTestCase.test_queries",
            "backends.tests.BackendTestCase.test_queries_bare_where",
            "backends.tests.BackendTestCase.test_queries_limit",
            "backends.tests.BackendTestCase.test_queries_logger",
            "backends.tests.BackendTestCase.test_unicode_fetches",
            "backends.tests.EscapingChecks",
            "backends.test_utils.CursorWrapperTests",
            "custom_methods.tests.MethodsTests.test_custom_methods",
            "delete_regress.tests.DeleteLockingTest.test_concurrent_delete",
            "expressions.tests.BasicExpressionsTests.test_annotate_values_filter",
            "expressions.tests.BasicExpressionsTests.test_filtering_on_rawsql_that_is_boolean",
            "expressions.tests.BasicExpressionsTests.test_order_by_multiline_sql",
            "migrations.test_commands.MigrateTests.test_migrate_plan",
            "migrations.test_multidb.MultiDBOperationTests.test_run_sql_migrate_foo_router_with_hints",
            "migrations.test_operations.OperationTests.test_run_sql",
            "migrations.test_operations.OperationTests.test_run_sql_params",
            "migrations.test_operations.OperationTests.test_separate_database_and_state",
            "model_fields.test_jsonfield.TestQuerying.test_key_sql_injection_escape",
            "model_fields.test_jsonfield.TestQuerying.test_key_transform_raw_expression",
            "model_fields.test_jsonfield.TestQuerying.test_nested_key_transform_raw_expression",
            "multiple_database.tests.QueryTestCase.test_raw",
            "prefetch_related.tests.RawQuerySetTests",
            "queries.tests.Queries1Tests.test_order_by_rawsql",
            "raw_query.tests.RawQueryTests",
            "schema.test_logging.SchemaLoggerTests.test_extra_args",
            "schema.tests.SchemaTests.test_remove_constraints_capital_letters",
            "test_utils.tests.AllowedDatabaseQueriesTests.test_allowed_database_copy_queries",
            "timezones.tests.LegacyDatabaseTests.test_cursor_execute_accepts_naive_datetime",
            "timezones.tests.LegacyDatabaseTests.test_cursor_execute_returns_naive_datetime",
            "timezones.tests.LegacyDatabaseTests.test_raw_sql",
            "timezones.tests.NewDatabaseTests.test_cursor_execute_accepts_naive_datetime",
            "timezones.tests.NewDatabaseTests.test_cursor_execute_returns_naive_datetime",
            "timezones.tests.NewDatabaseTests.test_cursor_explicit_time_zone",
            "timezones.tests.NewDatabaseTests.test_raw_sql",
            "view_tests.tests.test_debug.DebugViewQueriesAllowedTests.test_handle_db_exception",
        },
        "Custom aggregations/functions with SQL don't work on MongoDB.": {
            "aggregation.tests.AggregateTestCase.test_add_implementation",
            "aggregation.tests.AggregateTestCase.test_multi_arg_aggregate",
            "aggregation.tests.AggregateTestCase.test_empty_result_optimization",
            "annotations.tests.NonAggregateAnnotationTestCase.test_custom_functions",
            "annotations.tests.NonAggregateAnnotationTestCase.test_custom_functions_can_ref_other_functions",
        },
        "Bilateral transform not implemented.": {
            "db_functions.tests.FunctionTests.test_func_transform_bilateral",
            "db_functions.tests.FunctionTests.test_func_transform_bilateral_multivalue",
        },
        "MongoDB does not support this database function.": {
            "db_functions.datetime.test_now.NowTests",
            "db_functions.math.test_sign.SignTests",
            "db_functions.text.test_chr.ChrTests",
            "db_functions.text.test_md5.MD5Tests",
            "db_functions.text.test_ord.OrdTests",
            "db_functions.text.test_pad.PadTests",
            "db_functions.text.test_repeat.RepeatTests",
            "db_functions.text.test_reverse.ReverseTests",
            "db_functions.text.test_right.RightTests",
            "db_functions.text.test_sha1.SHA1Tests",
            "db_functions.text.test_sha224.SHA224Tests",
            "db_functions.text.test_sha256.SHA256Tests",
            "db_functions.text.test_sha384.SHA384Tests",
            "db_functions.text.test_sha512.SHA512Tests",
        },
        "ExtractQuarter database function not supported.": {
            "db_functions.datetime.test_extract_trunc.DateFunctionTests.test_extract_quarter_func",
            "db_functions.datetime.test_extract_trunc.DateFunctionTests.test_extract_quarter_func_boundaries",
        },
        "TruncDate database function's tzinfo not supported.": {
            "model_fields.test_datetimefield.DateTimeFieldTests.test_lookup_date_with_use_tz",
            "timezones.tests.NewDatabaseTests.test_query_convert_timezones",
        },
        "MongoDB can't annotate ($project) a function like PI().": {
            "aggregation.tests.AggregateTestCase.test_aggregation_default_using_decimal_from_database",
            "db_functions.math.test_pi.PiTests.test",
        },
        "Can't cast from date to datetime without MongoDB interpreting the new value in UTC.": {
            "db_functions.comparison.test_cast.CastTests.test_cast_from_db_date_to_datetime",
            "db_functions.comparison.test_cast.CastTests.test_cast_from_db_datetime_to_time",
        },
        "Casting Python literals doesn't work.": {
            "db_functions.comparison.test_cast.CastTests.test_cast_from_python",
            "db_functions.comparison.test_cast.CastTests.test_cast_from_python_to_date",
            "db_functions.comparison.test_cast.CastTests.test_cast_from_python_to_datetime",
            "db_functions.comparison.test_cast.CastTests.test_cast_to_duration",
        },
        "inspectdb is not supported.": {
            "inspectdb.tests.InspectDBTestCase",
            "inspectdb.tests.InspectDBTransactionalTests",
        },
        "DatabaseIntrospection.get_table_description() not supported.": {
            "introspection.tests.IntrospectionTests.test_bigautofield",
            "introspection.tests.IntrospectionTests.test_get_table_description_col_lengths",
            "introspection.tests.IntrospectionTests.test_get_table_description_names",
            "introspection.tests.IntrospectionTests.test_get_table_description_nullable",
            "introspection.tests.IntrospectionTests.test_get_table_description_types",
            "introspection.tests.IntrospectionTests.test_smallautofield",
        },
        "MongoDB can't introspect primary key.": {
            "introspection.tests.IntrospectionTests.test_get_primary_key_column",
            "schema.tests.SchemaTests.test_alter_primary_key_the_same_name",
            "schema.tests.SchemaTests.test_primary_key",
        },
        "Known issue querying JSONField.": {
            # An ExpressionWrapper annotation with KeyTransform followed by
            # .filter(expr__isnull=False) doesn't use KeyTransformIsNull as it
            # needs to.
            "model_fields.test_jsonfield.TestQuerying.test_expression_wrapper_key_transform",
            # There is no way to distinguish between a JSON "null" (represented
            # by Value(None, JSONField())) and a SQL null (queried using the
            # isnull lookup). Both of these queries return both nulls.
            "model_fields.test_jsonfield.TestSaveLoad.test_json_null_different_from_sql_null",
            # Some queries with Q objects, e.g. Q(value__foo="bar"), don't work
            # properly, particularly with QuerySet.exclude().
            "model_fields.test_jsonfield.TestQuerying.test_lookup_exclude",
            "model_fields.test_jsonfield.TestQuerying.test_lookup_exclude_nonexistent_key",
            # Queries like like QuerySet.filter(value__j=None) incorrectly
            # returns objects where the key doesn't exist.
            "model_fields.test_jsonfield.TestQuerying.test_none_key",
            "model_fields.test_jsonfield.TestQuerying.test_none_key_exclude",
        },
        "Queries without a collection aren't supported on MongoDB.": {
            "queries.test_q.QCheckTests",
            "queries.test_query.TestQueryNoModel",
        },
        "MongoDB doesn't use CursorDebugWrapper.": {
            # It prevents RuntimeWarning for import-time queries from working.
            # https://github.com/django/django/commit/fbd16438f46bc2128926958ad24331da5d1b406f
            "apps.tests.QueryPerformingAppTests",
            "backends.tests.LastExecutedQueryTest.test_last_executed_query",
            "backends.tests.LastExecutedQueryTest.test_last_executed_query_with_duplicate_params",
            "backends.tests.LastExecutedQueryTest.test_query_encoding",
        },
        "Test not applicable for MongoDB's SQLCompiler.": {
            "queries.test_iterator.QuerySetIteratorTests",
        },
        "Support for views not implemented.": {
            "introspection.tests.IntrospectionTests.test_table_names_with_views",
        },
        "Connection health checks not implemented.": {
            "backends.base.test_base.ConnectionHealthChecksTests",
        },
        "transaction.atomic() is not supported.": {
            "backends.base.test_base.DatabaseWrapperLoggingTests",
            "basic.tests.SelectOnSaveTests.test_select_on_save_lying_update",
            "migrations.test_executor.ExecutorTests.test_atomic_operation_in_non_atomic_migration",
            "migrations.test_operations.OperationTests.test_run_python_atomic",
        },
        "transaction.rollback() is not supported.": {
            "transactions.tests.AtomicMiscTests.test_mark_for_rollback_on_error_in_autocommit",
            "transactions.tests.AtomicMiscTests.test_mark_for_rollback_on_error_in_transaction",
            "transactions.tests.NonAutocommitTests.test_orm_query_after_error_and_rollback",
        },
        "migrate --fake-initial is not supported.": {
            "migrations.test_commands.MigrateTests.test_migrate_fake_initial",
            "migrations.test_commands.MigrateTests.test_migrate_fake_split_initial",
            "migrations.test_executor.ExecutorTests.test_soft_apply",
        },
        "Test works in isolation but fails on CI.": {
            # Probably something to do with lack of transaction support.
            "migration_test_data_persistence.tests.MigrationDataNormalPersistenceTestCase.test_persistence",
        },
        "Database caching not implemented.": {
            "cache.tests.CreateCacheTableForDBCacheTests",
            "cache.tests.DBCacheTests",
            "cache.tests.DBCacheWithTimeZoneTests",
        },
        "FilteredRelation not supported.": {
            # https://github.com/mongodb/django-mongodb-backend/issues/157
            "filtered_relation.tests.FilteredRelationAggregationTests",
            "filtered_relation.tests.FilteredRelationAnalyticalAggregationTests",
            "filtered_relation.tests.FilteredRelationTests",
            "queryset_pickle.tests.PickleabilityTestCase.test_pickle_filteredrelation",
        },
        "Broken test.": {
            # This test uses a database router that only allows the auth_user
            # table to be created on "other", but then writes users to
            # "default". It can raise IntegrityError when run alongside other
            # tests because the auth_user table isn't flushed between tests.
            "multiple_database.tests.AuthTestCase.test_dumpdata",
        },
        "ForeignObject is not supported.": {
            "foreign_object.test_agnostic_order_trimjoin.TestLookupQuery.test_deep_mixed_backward",
            "foreign_object.test_empty_join.RestrictedConditionsTests",
            "foreign_object.tests.MultiColumnFKTests",
            "foreign_object.tests.TestExtraJoinFilterQ",
        },
        "Tuple lookups are not supported.": {
            "foreign_object.test_tuple_lookups.TupleLookupsTests",
        },
        "ColPairs is not supported.": {
            "auth_tests.test_views.CustomUserCompositePrimaryKeyPasswordResetTest",
            "composite_pk.test_aggregate.CompositePKAggregateTests",
            "composite_pk.test_create.CompositePKCreateTests",
            "composite_pk.test_delete.CompositePKDeleteTests",
            "composite_pk.test_filter.CompositePKFilterTests",
            "composite_pk.test_get.CompositePKGetTests",
            "composite_pk.test_models.CompositePKModelsTests",
            "composite_pk.test_order_by.CompositePKOrderByTests",
            "composite_pk.test_update.CompositePKUpdateTests",
            "composite_pk.test_values.CompositePKValuesTests",
            "composite_pk.tests.CompositePKTests",
            "composite_pk.tests.CompositePKFixturesTests",
        },
        "Custom lookups are not supported.": {
            "custom_lookups.tests.BilateralTransformTests",
            "custom_lookups.tests.LookupTests.test_basic_lookup",
            "custom_lookups.tests.LookupTests.test_custom_name_lookup",
            "custom_lookups.tests.LookupTests.test_div3_extract",
            "custom_lookups.tests.SubqueryTransformTests.test_subquery_usage",
        },
        "connection.close() does not close the connection.": {
            "servers.test_liveserverthread.LiveServerThreadTest.test_closes_connections",
            "servers.tests.LiveServerTestCloseConnectionTest.test_closes_connections",
        },
        "Disallowed query protection doesn't work on MongoDB.": {
            # Because this backend doesn't use cursor(), chunked_cursor(), etc.
            # https://github.com/django/django/blob/045110ff3089aefd9c3e65c707df465bacfed986/django/test/testcases.py#L195-L206
            "test_utils.test_testcase.TestTestCase.test_disallowed_database_queries",
            "test_utils.test_transactiontestcase.DisallowedDatabaseQueriesTests.test_disallowed_database_queries",
            "test_utils.tests.DisallowedDatabaseQueriesTests.test_disallowed_database_chunked_cursor_queries",
            "test_utils.tests.DisallowedDatabaseQueriesTests.test_disallowed_database_queries",
            "test_utils.tests.DisallowedDatabaseQueriesTests.test_disallowed_thread_database_connection",
        },
    }

    @cached_property
    def django_test_skips(self):
        skips = super().django_test_skips
        skips.update(self._django_test_skips)
        return skips

    @cached_property
    def is_mongodb_6_3(self):
        return self.connection.get_database_version() >= (6, 3)

    @cached_property
    def supports_atlas_search(self):
        """Does the server support Atlas search queries and search indexes?"""
        try:
            # An existing collection must be used on MongoDB 6, otherwise
            # the operation will not error when unsupported.
            self.connection.get_collection("django_migrations").list_search_indexes()
        except OperationFailure:
            # It would be best to check the error message or error code to
            # avoid hiding some other exception, but the message/code varies
            # across MongoDB versions. Example error message:
            # "$listSearchIndexes  stage is only allowed on MongoDB Atlas".
            return False
        else:
            return True

    @cached_property
    def _supports_transactions(self):
        """
        Transactions are enabled if MongoDB is configured as a replica set or a
        sharded cluster. This is a MongoDB-specific feature flag distinct from Django's
        supports_transactions (without the underscore prefix).
        """
        self.connection.ensure_connection()
        client = self.connection.connection.admin
        hello = client.command("hello")
        # a replica set or a sharded cluster
        return "setName" in hello or hello.get("msg") == "isdbgrid"
