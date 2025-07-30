from contextlib import ContextDecorator

from django.db import DEFAULT_DB_ALIAS, DatabaseError
from django.db.transaction import get_connection, on_commit

__all__ = [
    "atomic",
    "on_commit",  # convenience alias
]


class Atomic(ContextDecorator):
    """
    Guarantee the atomic execution of a given block.

    Simplified from django.db.transaction.
    """

    def __init__(self, using):
        self.using = using

    def __enter__(self):
        connection = get_connection(self.using)
        if connection.in_atomic_block_mongo:
            # Track the number of nested atomic() calls.
            connection.nested_atomics += 1
        else:
            # Start a transaction for the outermost atomic().
            connection.start_transaction_mongo()
            connection.in_atomic_block_mongo = True

    def __exit__(self, exc_type, exc_value, traceback):
        connection = get_connection(self.using)
        if connection.nested_atomics:
            # Exiting inner atomic.
            connection.nested_atomics -= 1
        else:
            # Reset flag when exiting outer atomic.
            connection.in_atomic_block_mongo = False
        if exc_type is None:
            # atomic() exited without an error.
            if not connection.in_atomic_block_mongo:
                # Commit transaction if outer atomic().
                try:
                    connection.commit_mongo()
                except DatabaseError:
                    connection.rollback_mongo()
        else:
            # atomic() exited with an error.
            if not connection.in_atomic_block_mongo:
                # Rollback transaction if outer atomic().
                connection.rollback_mongo()


def atomic(using=None):
    # Bare decorator: @atomic -- although the first argument is called `using`,
    # it's actually the function being decorated.
    if callable(using):
        return Atomic(DEFAULT_DB_ALIAS)(using)
    # Decorator: @atomic(...) or context manager: with atomic(...): ...
    return Atomic(using)
