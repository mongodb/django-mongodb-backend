"""
These tests are adapted from Django's tests/raw_query/tests.py.
"""

from datetime import date, datetime

from django.core.exceptions import FieldDoesNotExist
from django.db import connection
from django.test import TestCase, skipUnlessDBFeature

from django_mongodb_backend import transaction
from django_mongodb_backend.queryset import RawQuerySet

from .models import (
    Author,
    Book,
    BookFkAsPk,
    Coffee,
    FriendlyAuthor,
    MixedCaseIDColumn,
    Reviewer,
)


class RawAggregateTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.a1 = Author.objects.create(first_name="Joe", last_name="Smith", dob=date(1950, 9, 20))
        cls.a2 = Author.objects.create(first_name="Jill", last_name="Doe", dob=date(1920, 4, 2))
        cls.a3 = Author.objects.create(first_name="Bob", last_name="Smith", dob=date(1986, 1, 25))
        cls.a4 = Author.objects.create(first_name="Bill", last_name="Jones", dob=date(1932, 5, 10))
        cls.b1 = Book.objects.create(
            title="The awesome book",
            author=cls.a1,
            paperback=False,
            opening_line=(
                "It was a bright cold day in April and the clocks were striking thirteen."
            ),
        )
        cls.b2 = Book.objects.create(
            title="The horrible book",
            author=cls.a1,
            paperback=True,
            opening_line=(
                "On an evening in the latter part of May a middle-aged man "
                "was walking homeward from Shaston to the village of Marlott, "
                "in the adjoining Vale of Blakemore, or Blackmoor."
            ),
        )
        cls.b3 = Book.objects.create(
            title="Another awesome book",
            author=cls.a1,
            paperback=False,
            opening_line="A squat gray building of only thirty-four stories.",
        )
        cls.b4 = Book.objects.create(
            title="Some other book",
            author=cls.a3,
            paperback=True,
            opening_line="It was the day my grandmother exploded.",
        )
        cls.c1 = Coffee.objects.create(brand="dunkin doughnuts")
        cls.c2 = Coffee.objects.create(brand="starbucks")
        cls.r1 = Reviewer.objects.create()
        cls.r2 = Reviewer.objects.create()
        cls.r1.reviewed.add(cls.b2, cls.b3, cls.b4)

    def assertSuccessfulRawQuery(
        self,
        model,
        query,
        expected_results,
        expected_annotations=(),
    ):
        """
        Execute the passed query against the passed model and check the output.
        """
        results = list(model.objects.raw_aggregate(query))
        expected_results = list(expected_results)
        with self.assertNumQueries(0):
            self.assertProcessed(model, results, expected_results, expected_annotations)
            self.assertAnnotations(results, expected_annotations)

    def assertProcessed(self, model, results, orig, expected_annotations=()):
        """Compare the results of a raw query against expected results."""
        self.assertEqual(len(results), len(orig))
        for index, item in enumerate(results):
            orig_item = orig[index]
            for annotation in expected_annotations:
                setattr(orig_item, *annotation)

            for field in model._meta.fields:
                # All values on the model are equal.
                self.assertEqual(getattr(item, field.attname), getattr(orig_item, field.attname))
                # This includes checking that they are the same type.
                self.assertEqual(
                    type(getattr(item, field.attname)),
                    type(getattr(orig_item, field.attname)),
                )

    def assertNoAnnotations(self, results):
        """The results of a raw query contain no annotations."""
        self.assertAnnotations(results, ())

    def assertAnnotations(self, results, expected_annotations):
        """The passed raw query results contain the expected annotations."""
        if expected_annotations:
            for index, result in enumerate(results):
                annotation, value = expected_annotations[index]
                self.assertTrue(hasattr(result, annotation))
                self.assertEqual(getattr(result, annotation), value)

    def test_rawqueryset_repr(self):
        queryset = RawQuerySet(pipeline=[])
        self.assertEqual(repr(queryset), "<RawQuerySet: []>")
        self.assertEqual(repr(queryset.query), "<RawQuery: []>")

    def test_simple_raw_query(self):
        """Basic test of raw query with a simple database query."""
        query = []
        authors = Author.objects.all()
        self.assertSuccessfulRawQuery(Author, query, authors)

    def test_raw_query_lazy(self):
        """
        Raw queries are lazy: they aren't actually executed until they're
        iterated over.
        """
        q = Author.objects.raw_aggregate([])
        self.assertIsNone(q.query.cursor)
        list(q)
        self.assertIsNotNone(q.query.cursor)

    def test_FK_raw_query(self):
        """
        Test of a simple raw query against a model containing a foreign key.
        """
        query = []
        books = Book.objects.all()
        self.assertSuccessfulRawQuery(Book, query, books)

    def test_db_column_handler(self):
        """
        Test of a simple raw query against a model containing a field with
        db_column defined.
        """
        query = []
        coffees = Coffee.objects.all()
        self.assertSuccessfulRawQuery(Coffee, query, coffees)

    def test_pk_with_mixed_case_db_column(self):
        """
        A raw query with a model that has a pk db_column with mixed case.
        """
        query = []
        queryset = MixedCaseIDColumn.objects.all()
        self.assertSuccessfulRawQuery(MixedCaseIDColumn, query, queryset)

    def test_order_handler(self):
        """
        Test of raw raw query's tolerance for columns being returned in any
        order.
        """
        selects = (
            ("dob, last_name, first_name, id"),
            ("last_name, dob, first_name, id"),
            ("first_name, last_name, dob, id"),
        )
        for select in selects:
            select = dict.fromkeys(select.split(", "), 1)
            query = [{"$project": select}]
            authors = Author.objects.all()
            self.assertSuccessfulRawQuery(Author, query, authors)

    def test_different_db_key_order(self):
        """
        A raw query correctly associates document keys to model fields when the
        document key order is different than the order of model fields.
        """
        author = Author(first_name="Out of", last_name="Order", dob=datetime(1950, 9, 20))
        # Insert a document with the keys reversed.
        connection.database.get_collection(Author._meta.db_table).insert_one(
            {
                field.name: getattr(author, field.name)
                for field in reversed(Author._meta.concrete_fields)
            }
        )
        query = []
        authors = Author.objects.all()
        self.assertSuccessfulRawQuery(Author, query, authors)

    def test_query_representation(self):
        """Test representation of raw query."""
        query = [{"$match": {"last_name": "foo"}}]
        qset = Author.objects.raw_aggregate(query)
        self.assertEqual(
            repr(qset),
            "<RawQuerySet: [{'$match': {'last_name': 'foo'}}]>",
        )
        self.assertEqual(
            repr(qset.query),
            "<RawQuery: [{'$match': {'last_name': 'foo'}}]>",
        )

    def test_many_to_many(self):
        """
        Test of a simple raw query against a model containing a m2m field.
        """
        query = []
        reviewers = Reviewer.objects.all()
        self.assertSuccessfulRawQuery(Reviewer, query, reviewers)

    def test_missing_fields(self):
        query = [{"$project": {"id": 1, "first_name": 1, "dob": 1}}]
        for author in Author.objects.raw_aggregate(query):
            self.assertIsNotNone(author.first_name)
            # last_name isn't given, but it will be retrieved on demand.
            self.assertIsNotNone(author.last_name)

    def test_missing_fields_without_PK(self):
        query = [{"$project": {"first_name": 1, "dob": 1, "_id": 0}}]
        msg = "Raw query must include the primary key"
        with self.assertRaisesMessage(FieldDoesNotExist, msg):
            list(Author.objects.raw_aggregate(query))

    def test_annotations(self):
        query = [
            {
                "$project": {
                    "first_name": 1,
                    "last_name": 1,
                    "dob": 1,
                    "birth_year": {"$year": "$dob"},
                },
            },
            {"$sort": {"_id": 1}},
        ]
        expected_annotations = (
            ("birth_year", 1950),
            ("birth_year", 1920),
            ("birth_year", 1986),
            ("birth_year", 1932),
        )
        authors = Author.objects.order_by("pk")
        self.assertSuccessfulRawQuery(Author, query, authors, expected_annotations)

    def test_multiple_iterations(self):
        query = []
        normal_authors = Author.objects.all()
        raw_authors = Author.objects.raw_aggregate(query)

        # First Iteration
        first_iterations = 0
        for index, raw_author in enumerate(raw_authors):
            self.assertEqual(normal_authors[index], raw_author)
            first_iterations += 1

        # Second Iteration
        second_iterations = 0
        for index, raw_author in enumerate(raw_authors):
            self.assertEqual(normal_authors[index], raw_author)
            second_iterations += 1

        self.assertEqual(first_iterations, second_iterations)

    def test_get_item(self):
        # Indexing on RawQuerySets
        query = [{"$sort": {"id": 1}}]
        third_author = Author.objects.raw_aggregate(query)[2]
        self.assertEqual(third_author.first_name, "Bob")

        first_two = Author.objects.raw_aggregate(query)[0:2]
        self.assertEqual(len(first_two), 2)

        with self.assertRaises(TypeError):
            Author.objects.raw_aggregate(query)["test"]

    def test_inheritance(self):
        f = FriendlyAuthor.objects.create(
            first_name="Wesley", last_name="Chun", dob=date(1962, 10, 28)
        )
        query = []
        self.assertEqual([o.pk for o in FriendlyAuthor.objects.raw_aggregate(query)], [f.pk])

    def test_query_count(self):
        self.assertNumQueries(1, list, Author.objects.raw_aggregate([]))

    def test_subquery_in_raw_sql(self):
        list(
            Book.objects.raw_aggregate(
                [{"$match": {"paperback": {"$ne": None}}}, {"$project": {"id": 1}}]
            )
        )

    def test_db_column_name_is_used_in_raw_query(self):
        """
        Regression test that ensures the `column` attribute on the field is
        used to generate the list of fields included in the query, as opposed
        to the `attname`. This is important when the primary key is a
        ForeignKey field because `attname` and `column` are not necessarily the
        same.
        """
        b = BookFkAsPk.objects.create(book=self.b1)
        self.assertEqual(
            list(
                BookFkAsPk.objects.raw_aggregate([{"$project": {"not_the_default": 1, "_id": 0}}])
            ),
            [b],
        )

    def test_result_caching(self):
        with self.assertNumQueries(1):
            books = Book.objects.raw_aggregate([])
            list(books)
            list(books)

    def test_iterator(self):
        with self.assertNumQueries(2):
            books = Book.objects.raw_aggregate([])
            list(books.iterator())
            list(books.iterator())

    def test_bool(self):
        self.assertIs(bool(Book.objects.raw_aggregate([])), True)
        self.assertIs(bool(Book.objects.raw_aggregate([{"$match": {"id": 0}}])), False)

    def test_len(self):
        self.assertEqual(len(Book.objects.raw_aggregate([])), 4)
        self.assertEqual(len(Book.objects.raw_aggregate([{"$match": {"id": 0}}])), 0)

    @skipUnlessDBFeature("_supports_transactions")
    def test_transaction(self):
        count = Author.objects.count()
        with self.assertRaisesMessage(Exception, "Oops"), transaction.atomic():
            Author.objects.update(last_name="Haddock")
            # Changes within in a transaction are visible to raw_aggregate().
            query = [{"$match": {"last_name": "Haddock"}}]
            self.assertEqual(len(Author.objects.raw_aggregate(query)), count)
            raise Exception("Oops")
