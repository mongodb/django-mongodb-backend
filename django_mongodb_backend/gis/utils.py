"""
A collection of utility routines and classes used by the spatial
backend.
"""

from django.contrib.gis.db.backends.utils import SpatialOperator as _SpatialOperator


class SpatialOperator(_SpatialOperator):
    """
    Class encapsulating the behavior specific to a GIS operation (used by lookups).
    """

    def __init__(self, op=None, func=None):
        self.op = op
        self.func = func

    def as_mql(self, lhs, rhs, params=None):
        return self.func(lhs, rhs, self.op, params)
