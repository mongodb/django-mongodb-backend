from .expression_converters import convert_expression


def convert_expr_to_match(query):
    """
    Optimize an MQL query by converting conditions into a list of $match
    stages.
    """
    if "$expr" not in query:
        return [query]
    if query["$expr"] == {}:
        return [{"$match": {}}]
    return _process_expression(query["$expr"])


def _process_expression(expr):
    """Process an expression and extract optimizable conditions."""
    match_conditions = []
    remaining_conditions = []
    if isinstance(expr, dict):
        has_and = "$and" in expr
        has_or = "$or" in expr
        # Do a top-level check for $and or $or because these should inform.
        # If they fail, they should failover to a remaining conditions list.
        # There's probably a better way to do this.
        if has_and:
            and_match_conditions = _process_logical_conditions("$and", expr["$and"])
            match_conditions.extend(and_match_conditions)
        if has_or:
            or_match_conditions = _process_logical_conditions("$or", expr["$or"])
            match_conditions.extend(or_match_conditions)
        if not has_and and not has_or:
            # Process single condition.
            if optimized := convert_expression(expr):
                match_conditions.append({"$match": optimized})
            else:
                remaining_conditions.append({"$match": {"$expr": expr}})
    else:
        # Can't optimize.
        remaining_conditions.append({"$expr": expr})
    return match_conditions + remaining_conditions


def _process_logical_conditions(logical_op, logical_conditions):
    """Process conditions within a logical array."""
    optimized_conditions = []
    match_conditions = []
    remaining_conditions = []
    for condition in logical_conditions:
        _remaining_conditions = []
        if isinstance(condition, dict):
            if optimized := convert_expression(condition):
                optimized_conditions.append(optimized)
            else:
                _remaining_conditions.append(condition)
        else:
            _remaining_conditions.append(condition)
        if _remaining_conditions:
            # Any expressions that can't be optimized must remain in a $expr
            # that preserves the logical operator.
            if len(_remaining_conditions) > 1:
                remaining_conditions.append({"$expr": {logical_op: _remaining_conditions}})
            else:
                remaining_conditions.append({"$expr": _remaining_conditions[0]})
    if optimized_conditions:
        optimized_conditions.extend(remaining_conditions)
        if len(optimized_conditions) > 1:
            match_conditions.append({"$match": {logical_op: optimized_conditions}})
        else:
            match_conditions.append({"$match": optimized_conditions[0]})
    else:
        match_conditions.append({"$match": {logical_op: remaining_conditions}})
    return match_conditions
