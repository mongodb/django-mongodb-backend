from django_mongodb_backend.query_conversion.expression_converters import convert_expression


class QueryOptimizer:
    def convert_expr_to_match(self, expr_query):
        """
        Takes an MQL query with $expr and optimizes it by extracting
        optimizable conditions into separate $match stages.

        Args:
            expr_query: Dictionary containing the $expr query

        Returns:
            List of optimized match conditions
        """
        if "$expr" not in expr_query:
            return [expr_query]

        if expr_query["$expr"] == {}:
            return [{"$match": {}}]

        expr_content = expr_query["$expr"]

        # Handle the expression content
        return self._process_expression(expr_content)

    def _process_expression(self, expr):
        """
        Process an expression and extract optimizable conditions.

        Args:
            expr: The expression to process
        """
        match_conditions = []
        remaining_conditions = []
        if isinstance(expr, dict):
            # Check if this is an $and operation
            has_and = "$and" in expr
            has_or = "$or" in expr
            # Do a top-level check for $and or $or because these should inform
            # If they fail, they should failover to a remaining conditions list
            # There's probably a better way to do this, but this is a start
            if has_and:
                and_match_conditions = self._process_logical_conditions("$and", expr["$and"])
                match_conditions.extend(and_match_conditions)
            if has_or:
                or_match_conditions = self._process_logical_conditions("$or", expr["$or"])
                match_conditions.extend(or_match_conditions)
            if not has_and and not has_or:
                # Process single condition
                optimized = convert_expression(expr)
                if optimized:
                    match_conditions.append({"$match": optimized})
                else:
                    remaining_conditions.append({"$match": {"$expr": expr}})
        else:
            # Can't optimize
            remaining_conditions.append({"$expr": expr})
        return match_conditions + remaining_conditions

    def _process_logical_conditions(self, logical_op, logical_conditions):
        """
        Process conditions within a logical array.

        Args:
            logical_conditions: List of conditions within logical operator
        """
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
                # Any expressions we can't optimize must remain
                # in an $expr that preserves the logical operator
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
