"""Not a public API."""

from bson import SON, Decimal128, ObjectId


class MongoTestCaseMixin:
    maxDiff = None
    query_types = {"SON": SON, "ObjectId": ObjectId, "Decimal128": Decimal128}

    def assertAggregateQuery(self, query, expected_collection, expected_pipeline):
        """
        Assert that the logged query is equal to:
            db.{expected_collection}.aggregate({expected_pipeline})
        """
        prefix, pipeline = query.split("(", 1)
        _, collection, operator = prefix.split(".")
        self.assertEqual(operator, "aggregate")
        self.assertEqual(collection, expected_collection)
        self.assertEqual(eval(pipeline[:-1], self.query_types, {}), expected_pipeline)  # noqa: S307

    def assertInsertQuery(self, query, expected_collection, expected_documents):
        """
        Assert that the logged query is equal to:
            db.{expected_collection}.insert_many({expected_documents})
        """
        prefix, pipeline = query.split("(", 1)
        _, collection, operator = prefix.split(".")
        self.assertEqual(operator, "insert_many")
        self.assertEqual(collection, expected_collection)
        self.assertEqual(eval(pipeline[:-1], self.query_types), expected_documents)  # noqa: S307

    def assertUpdateQuery(self, query, expected_collection, expected_condition, expected_set):
        """
        Assert that the logged query is equal to:
            db.{expected_collection}.update_many({expected_condition}, {expected_set})
        """
        prefix, pipeline = query.split("(", 1)
        _, collection, operator = prefix.split(".")
        self.assertEqual(operator, "update_many")
        self.assertEqual(collection, expected_collection)
        condition, set_expression = eval(pipeline[:-1], self.query_types, {})  # noqa: S307
        self.assertEqual(condition, expected_condition)
        self.assertEqual(set_expression, expected_set)
