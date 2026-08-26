from django.db import NotSupportedError
from django.db.models.functions.uuid import UUID4, UUID7


def uuid4(self, compiler, connection, as_expr=False):  # noqa: ARG001
    raise NotSupportedError("UUID4 is not supported on this database backend.")


def uuid7(self, compiler, connection, as_expr=False):  # noqa: ARG001
    raise NotSupportedError("UUID7 is not supported on this database backend.")


def register_uuid():
    UUID4.as_mql = uuid4
    UUID7.as_mql = uuid7
