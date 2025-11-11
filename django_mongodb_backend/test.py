"""Not a public API."""

from bson import SON, Decimal128, ObjectId


class MongoTestCaseMixin:
    maxDiff = None

    COMMUTATIVE_OPERATORS = {"$and", "$or", "$all"}

    @staticmethod
    def _normalize_query(obj):
        if isinstance(obj, dict):
            normalized = {}
            for k, v in obj.items():
                if k in MongoTestCaseMixin.COMMUTATIVE_OPERATORS and isinstance(v, list):
                    # Only sort for commutative operators
                    normalized[k] = sorted(
                        (MongoTestCaseMixin._normalize_query(i) for i in v), key=lambda x: str(x)
                    )
                else:
                    normalized[k] = MongoTestCaseMixin._normalize_query(v)
            return normalized

        if isinstance(obj, list):
            # Lists not under commutative ops keep their order
            return [MongoTestCaseMixin._normalize_query(i) for i in obj]

        return obj

    def assertAggregateQuery(self, query, expected_collection, expected_pipeline):
        """
        Assert that the logged query is equal to:
            db.{expected_collection}.aggregate({expected_pipeline})
        """
        prefix, pipeline = query.split("(", 1)
        _, collection, operator = prefix.split(".")
        self.assertEqual(operator, "aggregate")
        self.assertEqual(collection, expected_collection)
        self.assertEqual(
            self._normalize_query(
                eval(  # noqa: S307
                    pipeline[:-1], {"SON": SON, "ObjectId": ObjectId, "Decimal128": Decimal128}, {}
                )
            ),
            self._normalize_query(expected_pipeline),
        )
