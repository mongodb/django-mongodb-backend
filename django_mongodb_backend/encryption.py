# Queryable Encryption helper classes


class EqualityQuery(dict):
    def __init__(self, *, contention=None):
        super().__init__(queryType="equality")
        if contention is not None:
            self["contention"] = contention


class RangeQuery(dict):
    def __init__(
        self, *, contention=None, max=None, min=None, precision=None, sparsity=None, trimFactor=None
    ):
        super().__init__(queryType="range")
        options = {
            "contention": contention,
            "max": max,
            "min": min,
            "precision": precision,
            "sparsity": sparsity,
            "trimFactor": trimFactor,
        }
        self.update({k: v for k, v in options.items() if v is not None})
