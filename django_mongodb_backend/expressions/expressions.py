from django.db.models.expressions import Func


class Remove(Func):
    def as_mql(self, compiler, connection, as_expr=False):
        return "$$REMOVE"
