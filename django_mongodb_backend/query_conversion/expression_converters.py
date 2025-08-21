class BaseConverter:
    """Base class for $expr to $match converters."""

    @classmethod
    def convert(cls, expr):
        raise NotImplementedError("Subclasses must implement this method.")

    @classmethod
    def is_simple_value(cls, value):
        """Is the value is a simple type (not a dict)?"""
        if value is None:
            return True
        if isinstance(value, str) and value.startswith("$"):
            return False
        if isinstance(value, (list, tuple, set)):
            return all(cls.is_simple_value(v) for v in value)
        # TODO: Support `$getField` conversion.
        return not isinstance(value, dict)


class BinaryConverter(BaseConverter):
    """
    Base class for converting binary operations.

    For example:
        "$expr": {
            {"$gt": ["$price", 100]}
        }
    is converted to:
        {"$gt": ["price", 100]}
    """

    operator: str

    @classmethod
    def convert(cls, args):
        if isinstance(args, list) and len(args) == 2:
            field_expr, value = args
            # Check if first argument is a simple field reference.
            if (
                isinstance(field_expr, str)
                and field_expr.startswith("$")
                and cls.is_simple_value(value)
            ):
                field_name = field_expr[1:]  # Remove the $ prefix.
                if cls.operator == "$eq":
                    return {field_name: value}
                return {field_name: {cls.operator: value}}
        return None


class EqConverter(BinaryConverter):
    """
    Convert $eq operation to a $match query.

    For example:
        "$expr": {
                {"$eq": ["$status", "active"]}
        }
    is converted to:
        {"status": "active"}
    """

    operator = "$eq"


class GtConverter(BinaryConverter):
    operator = "$gt"


class GteConverter(BinaryConverter):
    operator = "$gte"


class LtConverter(BinaryConverter):
    operator = "$lt"


class LteConverter(BinaryConverter):
    operator = "$lte"


class InConverter(BaseConverter):
    """
    Convert $in operation to a $match query.

    For example:
        "$expr": {
            {"$in": ["$category", ["electronics", "books"]]}
        }
    is converted to:
        {"category": {"$in": ["electronics", "books"]}}
    """

    @classmethod
    def convert(cls, in_args):
        if isinstance(in_args, list) and len(in_args) == 2:
            field_expr, values = in_args
            # Check if first argument is a simple field reference.
            if isinstance(field_expr, str) and field_expr.startswith("$"):
                field_name = field_expr[1:]  # Remove the $ prefix.
                if isinstance(values, (list, tuple, set)) and all(
                    cls.is_simple_value(v) for v in values
                ):
                    return {field_name: {"$in": values}}
        return None


class LogicalConverter(BaseConverter):
    """
    Base class for converting logical operations to a $match query.

    For example:
        "$expr": {
            "$or": [
                {"$eq": ["$status", "active"]},
                {"$in": ["$category", ["electronics", "books"]]},
            ]
        }
    is converted to:
        "$or": [
            {"status": "active"},
            {"category": {"$in": ["electronics", "books"]}},
        ]
    """

    @classmethod
    def convert(cls, combined_conditions):
        if isinstance(combined_conditions, list):
            optimized_conditions = []
            for condition in combined_conditions:
                if isinstance(condition, dict) and len(condition) == 1:
                    if optimized_condition := convert_expression(condition):
                        optimized_conditions.append(optimized_condition)
                    else:
                        # Any failure should stop optimization.
                        return None
            if optimized_conditions:
                return {cls._logical_op: optimized_conditions}
        return None


class OrConverter(LogicalConverter):
    _logical_op = "$or"


class AndConverter(LogicalConverter):
    _logical_op = "$and"


OPTIMIZABLE_OPS = {
    "$eq": EqConverter,
    "$in": InConverter,
    "$and": AndConverter,
    "$or": OrConverter,
    "$gt": GtConverter,
    "$gte": GteConverter,
    "$lt": LtConverter,
    "$lte": LteConverter,
}


def convert_expression(expr):
    """
    Optimize MQL by converting an $expr condition to $match. Return the $match
    MQL, or None if not optimizable.
    """
    if isinstance(expr, dict) and len(expr) == 1:
        op = next(iter(expr.keys()))
        if op in OPTIMIZABLE_OPS:
            return OPTIMIZABLE_OPS[op].convert(expr[op])
    return None
