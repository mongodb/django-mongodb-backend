import datetime
from decimal import Decimal

from django.db.models import Count, Max, Q
from django.test import TestCase

from .models import Author, Book


class FilteredAggregateTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.a1 = Author.objects.create(name="test", age=40)
        cls.a2 = Author.objects.create(name="test2", age=60)
        cls.a3 = Author.objects.create(name="test3", age=40)
        cls.b1 = Book.objects.create(
            isbn="159059725",
            name="The Definitive Guide to Django: Web Development Done Right",
            pages=447,
            rating=4.5,
            price=Decimal("30.00"),
            contact=cls.a1,
            pubdate=datetime.date(2007, 12, 6),
        )
        cls.b2 = Book.objects.create(
            isbn="067232959",
            name="Sams Teach Yourself Django in 24 Hours",
            pages=528,
            rating=3.0,
            price=Decimal("30.00"),
            contact=cls.a2,
            pubdate=datetime.date(2008, 3, 3),
        )
        cls.b3 = Book.objects.create(
            isbn="159059996",
            name="Practical Django Projects",
            pages=600,
            rating=40.5,
            price=Decimal("30.00"),
            contact=cls.a3,
            pubdate=datetime.date(2008, 6, 23),
        )
        cls.a1.friends.add(cls.a2)
        cls.a1.friends.add(cls.a3)
        cls.b1.authors.add(cls.a1)
        cls.b1.authors.add(cls.a3)
        cls.b2.authors.add(cls.a2)
        cls.b3.authors.add(cls.a3)

    def test_filtered_aggregate_empty_condition_distinct(self):
        book = Book.objects.annotate(
            ages=Count("authors__age", filter=Q(authors__in=[]), distinct=True),
        ).get(pk=self.b1.pk)
        self.assertEqual(book.ages, 0)
        aggregate = Book.objects.aggregate(max_rating=Max("rating", filter=Q(rating__in=[])))
        self.assertEqual(aggregate, {"max_rating": None})

    def test_filtered_aggregate_full_condition(self):
        book = Book.objects.annotate(
            ages=Count("authors__age", filter=~Q(pk__in=[])),
        ).get(pk=self.b1.pk)
        self.assertEqual(book.ages, 2)
        aggregate = Book.objects.aggregate(max_rating=Max("rating", filter=~Q(rating__in=[])))
        self.assertEqual(aggregate, {"max_rating": 40.5})

    def test_filtered_aggregate_full_condition_distinct(self):
        book = Book.objects.annotate(
            ages=Count("authors__age", filter=~Q(authors__in=[]), distinct=True),
        ).get(pk=self.b1.pk)
        self.assertEqual(book.ages, 1)
        aggregate = Book.objects.aggregate(max_rating=Max("rating", filter=~Q(rating__in=[])))
        self.assertEqual(aggregate, {"max_rating": 40.5})
