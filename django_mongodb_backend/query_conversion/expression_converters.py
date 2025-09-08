"""Expression To Match Converters"""


class BaseConverter:
    """
    Base class for optimizers that handle specific operations in MQL queries.
    """

    @classmethod
    def convert(cls, expr):
        raise NotImplementedError("Subclasses must implement this method.")

    @classmethod
    def is_simple_field_name(cls, field_name):
        return (
            isinstance(field_name, str)
            and field_name != ""
            and field_name.startswith("$")
            # Special case for _ separated field names
            and field_name[1:].replace("_", "").isalnum()
        )

    @classmethod
    def is_simple_get_field(cls, get_field_object):
        if not isinstance(get_field_object, dict):
            return False

        get_field_expr = get_field_object.get("$getField")

        if (
            isinstance(get_field_expr, dict)
            and "input" in get_field_expr
            and "field" in get_field_expr
        ):
            input_expr = get_field_expr["input"]
            field_name = get_field_expr["field"]
            return cls.convert_field_name(input_expr) and (
                isinstance(field_name, str) and not field_name.startswith("$")
            )
        return False

    @classmethod
    def convert_field_name(cls, field_name):
        if cls.is_simple_field_name(field_name):
            return field_name[1:]
        if cls.is_simple_get_field(field_name):
            get_field_input = field_name["$getField"]["input"]
            get_field_field = field_name["$getField"]["field"]
            return f"{cls.convert_field_name(get_field_input)}.{get_field_field}"
        return None

    @classmethod
    def is_simple_value(cls, value):
        """Is the value is a simple type (not a dict)?"""
        if value is None:
            return True
        if isinstance(value, str) and value.startswith("$"):
            return False
        if isinstance(value, (list, tuple, set)):
            return all(cls.is_simple_value(v) for v in value)
        return not isinstance(value, dict)


class BinaryConverter(BaseConverter):
    """
    Base class for optimizers that handle binary expression operations in MQL queries.
    """

    operator: str

    @classmethod
    def convert(cls, args):
        if isinstance(args, list) and len(args) == 2:
            field_expr, value = args
            # Check if first argument is a simple field reference.
            if (field_name := cls.convert_field_name(field_expr)) and cls.is_simple_value(value):
                if cls.operator == "$eq":
                    return {field_name: value}
                return {field_name: {cls.operator: value}}

        return None


class EqConverter(BinaryConverter):
    """Convert $eq operation to a $match compatible query.

    For example::
        "$expr": {
                {"$eq": ["$status", "active"]}
        }
    is converted to::
        {"status": "active"}
    """

    operator = "$eq"


class GtConverter(BinaryConverter):
    """Convert $gt operation to a $match compatible query.

    For example::
        "$expr": {
            {"$gt": ["$price", 100]}
        }
    is converted to::
        {"$gt": ["price", 100]}
    """

    operator = "$gt"


class GteConverter(BinaryConverter):
    """Convert $gte operation to a $match compatible query.

    For example::
        "$expr": {
            {"$gte": ["$price", 100]}
        }
    is converted to::
        {"price": {"$gte", 100}}
    """

    operator = "$gte"


class LtConverter(BinaryConverter):
    """Convert $lt operation to a $match compatible query.

    For example::
        "$expr": {
            {"$lt": ["$price", 100]}
        }
    is converted to::
        {"$lt": ["price", 100]}
    """

    operator = "$lt"


class LteConverter(BinaryConverter):
    """Convert $lte operation to a $match compatible query.

    For example::
        "$expr": {
            {"$lte": ["$price", 100]}
        }
    is converted to::
        {"price": {"$lte", 100}}
    """

    operator = "$lte"


class InConverter(BaseConverter):
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
            # Check if second argument is a list of simple values
            if (field_name := cls.convert_field_name(field_expr)) and (
                isinstance(values, list | tuple | set)
                and all(cls.is_simple_value(v) for v in values)
            ):
                return {field_name: {"$in": values}}
        return None


class LogicalConverter(BaseConverter):
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


class OrConverter(LogicalConverter):
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


class AndConverter(LogicalConverter):
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
