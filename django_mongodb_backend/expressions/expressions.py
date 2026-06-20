from django.db.models.expressions import Func


class NullSafeArraySum(Func):
    """
    Compute the sum of an array column, returning None if the array is empty.
    Used as the project-stage replacement for Sum with filter to match SQL
    SUM() semantics (NULL for no rows, rather than MongoDB's $sum returning 0).
    """

    def as_mql(self, compiler, connection, as_expr=False):
        col_expr = self.source_expressions[0]
        # When a collection is empty, the wrapping stage injects an empty
        # document to support default= on aggregates — that document has no
        # array field at all, so $size gets missing type. $ifNull guards
        # against that.
        array_mql = {"$ifNull": [col_expr.as_mql(compiler, connection, as_expr=True), []]}
        mql = {
            "$cond": [
                {"$eq": [{"$size": array_mql}, 0]},
                None,
                {"$sum": array_mql},
            ]
        }
        return mql if as_expr else {"$expr": mql}


class Remove(Func):
    def as_mql(self, compiler, connection, as_expr=False):
        return "$$REMOVE"
