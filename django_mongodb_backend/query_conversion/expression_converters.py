"""Expression To Match Converters"""


class _BaseExpressionConverter:
    """
    Base class for optimizers that handle specific operations in MQL queries.
    This class can be extended to implement optimizations for other operations.
    """

    @classmethod
    def convert(cls, expr):
        raise NotImplementedError("Subclasses should implement this method.")

    @classmethod
    def is_simple_value(cls, value):
        """
        Check if the value is a simple type (not a dict).
        """
        if isinstance(value, str) and value.startswith("$"):
            return False
        if isinstance(value, (list, tuple, set)):  # noqa: UP038
            return all(cls.is_simple_value(v) for v in value)
        # TODO: Expand functionality to support `$getField` conversion
        return not isinstance(value, dict) or value is None


class _EqExpressionConverter(_BaseExpressionConverter):
    """Convert $eq operation to a $match compatible query.

    For example::
        "$expr": {
                {"$eq": ["$status", "active"]}
        }
    is converted to::
        {"status": "active"}
    """

    @classmethod
    def convert(cls, eq_args):
        if isinstance(eq_args, list) and len(eq_args) == 2:
            field_expr, value = eq_args

            # Check if first argument is a simple field reference
            if (
                isinstance(field_expr, str)
                and field_expr.startswith("$")
                and cls.is_simple_value(value)
            ):
                field_name = field_expr[1:]  # Remove the $ prefix
                return {field_name: value}

        return None


class _GtExpressionConverter(_BaseExpressionConverter):
    """Convert $gt operation to a $match compatible query.

    For example::
        "$expr": {
            {"$gt": ["$price", 100]}
        }
    is converted to::
        {"$gt": ["price", 100]}
    """

    @classmethod
    def convert(cls, gt_args):
        if isinstance(gt_args, list) and len(gt_args) == 2:
            field_expr, value = gt_args

            # Check if first argument is a simple field reference
            if (
                isinstance(field_expr, str)
                and field_expr.startswith("$")
                and cls.is_simple_value(value)
            ):
                field_name = field_expr[1:]  # Remove the $ prefix
                return {field_name: {"$gt": value}}

        return None


class _GteExpressionConverter(_BaseExpressionConverter):
    """Convert $gte operation to a $match compatible query.

    For example::
        "$expr": {
            {"$gte": ["$price", 100]}
        }
    is converted to::
        {"price": {"$gte", 100}}
    """

    @classmethod
    def convert(cls, gte_args):
        if isinstance(gte_args, list) and len(gte_args) == 2:
            field_expr, value = gte_args

            # Check if first argument is a simple field reference
            if (
                isinstance(field_expr, str)
                and field_expr.startswith("$")
                and cls.is_simple_value(value)
            ):
                field_name = field_expr[1:]  # Remove the $ prefix
                return {field_name: {"$gte": value}}

        return None


class _LtExpressionConverter(_BaseExpressionConverter):
    """Convert $lt operation to a $match compatible query.

    For example::
        "$expr": {
            {"$lt": ["$price", 100]}
        }
    is converted to::
        {"$lt": ["price", 100]}
    """

    @classmethod
    def convert(cls, lt_args):
        if isinstance(lt_args, list) and len(lt_args) == 2:
            field_expr, value = lt_args

            # Check if first argument is a simple field reference
            if (
                isinstance(field_expr, str)
                and field_expr.startswith("$")
                and cls.is_simple_value(value)
            ):
                field_name = field_expr[1:]  # Remove the $ prefix
                return {field_name: {"$lt": value}}

        return None


class _LteExpressionConverter(_BaseExpressionConverter):
    """Convert $lte operation to a $match compatible query.

    For example::
        "$expr": {
            {"$lte": ["$price", 100]}
        }
    is converted to::
        {"price": {"$lte", 100}}
    """

    @classmethod
    def convert(cls, lte_args):
        if isinstance(lte_args, list) and len(lte_args) == 2:
            field_expr, value = lte_args

            # Check if first argument is a simple field reference
            if (
                isinstance(field_expr, str)
                and field_expr.startswith("$")
                and cls.is_simple_value(value)
            ):
                field_name = field_expr[1:]  # Remove the $ prefix
                return {field_name: {"$lte": value}}

        return None


class _InExpressionConverter(_BaseExpressionConverter):
    """Convert $in operation to a $match compatible query.

    For example::
        "$expr": {
            {"$in": ["$category", ["electronics", "books"]]}
        }
    is converted to::
        {"category": {"$in": ["electronics", "books"]}}
    """

    @classmethod
    def convert(cls, in_args):
        if isinstance(in_args, list) and len(in_args) == 2:
            field_expr, values = in_args

            # Check if first argument is a simple field reference
            if isinstance(field_expr, str) and field_expr.startswith("$"):
                field_name = field_expr[1:]  # Remove the $ prefix
                if isinstance(values, list | tuple | set) and all(
                    cls.is_simple_value(v) for v in values
                ):
                    return {field_name: {"$in": values}}

        return None


class _LogicalExpressionConverter(_BaseExpressionConverter):
    """Generic for converting logical operations to a $match compatible query."""

    @classmethod
    def convert(cls, combined_conditions):
        if isinstance(combined_conditions, list):
            optimized_conditions = []
            for condition in combined_conditions:
                if isinstance(condition, dict) and len(condition) == 1:
                    if optimized_condition := convert_expression(condition):
                        optimized_conditions.append(optimized_condition)
                    else:
                        # Any failure should stop optimization
                        return None
            if optimized_conditions:
                return {cls._logical_op: optimized_conditions}
        return None


class _OrExpressionConverter(_LogicalExpressionConverter):
    """Convert $or operation to a $match compatible query.

    For example::
        "$expr": {
            "$or": [
                {"$eq": ["$status", "active"]},
                {"$in": ["$category", ["electronics", "books"]]},
            ]
        }
    is converted to::
        "$or": [
            {"status": "active"},
            {"category": {"$in": ["electronics", "books"]}},
        ]
    """

    _logical_op = "$or"


class _AndExpressionConverter(_LogicalExpressionConverter):
    """Convert $and operation to a $match compatible query.

    For example::
        "$expr": {
            "$and": [
                {"$eq": ["$status", "active"]},
                {"$in": ["$category", ["electronics", "books"]]},
                {"$eq": ["$verified", True]},
            ]
        }
    is converted to::
        "$and": [
            {"status": "active"},
            {"category": {"$in": ["electronics", "books"]}},
            {"verified": True},
        ]
    """

    _logical_op = "$and"


OPTIMIZABLE_OPS = {
    "$eq": _EqExpressionConverter,
    "$in": _InExpressionConverter,
    "$and": _AndExpressionConverter,
    "$or": _OrExpressionConverter,
    "$gt": _GtExpressionConverter,
    "$gte": _GteExpressionConverter,
    "$lt": _LtExpressionConverter,
    "$lte": _LteExpressionConverter,
}


def convert_expression(expr):
    """
    Optimize an MQL expression by extracting optimizable conditions.

    Args:
        expr: Dictionary containing the MQL expression

    Returns:
        Optimized match condition or None if not optimizable
    """
    if isinstance(expr, dict) and len(expr) == 1:
        op = next(iter(expr.keys()))
        if op in OPTIMIZABLE_OPS:
            return OPTIMIZABLE_OPS[op].convert(expr[op])
    return None
