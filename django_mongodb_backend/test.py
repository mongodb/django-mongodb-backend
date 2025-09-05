"""Not a public API."""

from bson import SON, ObjectId


class MongoTestCaseMixin:
    maxDiff = None

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
            eval(pipeline[:-1], {"SON": SON, "ObjectId": ObjectId}, {}),  # noqa: S307
            expected_pipeline,
        )
