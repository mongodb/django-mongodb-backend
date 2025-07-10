import unittest
from collections.abc import Callable
from time import monotonic, sleep

from django.db import connection
from django.db.utils import DatabaseError
from django.test import TransactionTestCase
from pymongo.operations import SearchIndexModel

from django_mongodb_backend.expressions.search import (
    CompoundExpression,
    SearchAutocomplete,
    SearchEquals,
    SearchExists,
    SearchGeoShape,
    SearchGeoWithin,
    SearchIn,
    SearchMoreLikeThis,
    SearchPhrase,
    SearchRange,
    SearchRegex,
    SearchText,
    SearchVector,
    SearchWildcard,
)

from .models import Article


def _wait_for_assertion(timeout: float = 120, interval: float = 0.5) -> None:
    """Generic to block until the predicate returns true

    Args:
        timeout (float, optional): Wait time for predicate. Defaults to TIMEOUT.
        interval (float, optional): Interval to check predicate. Defaults to DELAY.

    Raises:
        AssertionError: _description_
    """

    @staticmethod
    def _inner_wait_loop(predicate: Callable):
        """
        Waits until the given predicate stops raising AssertionError or DatabaseError.

        Args:
            predicate (Callable): A function that raises AssertionError (or DatabaseError)
                if a condition is not yet met. It should refresh its query each time
                it's called (e.g., by using `qs.all()` to avoid cached results).

        Raises:
            AssertionError or DatabaseError: If the predicate keeps failing beyond the timeout.
        """
        start = monotonic()
        while True:
            try:
                predicate()
            except (AssertionError, DatabaseError):
                if monotonic() - start > timeout:
                    raise
                sleep(interval)
            else:
                break

    return _inner_wait_loop


class SearchUtilsMixin(TransactionTestCase):
    available_apps = []

    @staticmethod
    def _get_collection(model):
        return connection.database.get_collection(model._meta.db_table)

    @staticmethod
    def create_search_index(model, index_name, definition, type="search"):
        collection = SearchUtilsMixin._get_collection(model)
        idx = SearchIndexModel(definition=definition, name=index_name, type=type)
        collection.create_search_index(idx)

    def _tear_down(self, model):
        collection = SearchUtilsMixin._get_collection(model)
        for search_indexes in collection.list_search_indexes():
            collection.drop_search_index(search_indexes["name"])
        collection.delete_many({})

    wait_for_assertion = _wait_for_assertion(timeout=3)


class SearchTest(SearchUtilsMixin):
    @classmethod
    def setUpTestData(cls):
        cls.create_search_index(
            Article,
            "equals_headline_index",
            {"mappings": {"dynamic": False, "fields": {"headline": {"type": "token"}}}},
        )


class SearchEqualsTest(SearchUtilsMixin):
    def setUp(self):
        self.create_search_index(
            Article,
            "equals_headline_index",
            {"mappings": {"dynamic": False, "fields": {"headline": {"type": "token"}}}},
        )
        self.article = Article.objects.create(headline="cross", number=1, body="body")
        Article.objects.create(headline="other thing", number=2, body="body")

    def test_search_equals(self):
        qs = Article.objects.annotate(score=SearchEquals(path="headline", value="cross"))
        self.wait_for_assertion(lambda: self.assertCountEqual(qs.all(), [self.article]))

    def tearDown(self):
        self._tear_down(Article)
        super().tearDown()


class SearchAutocompleteTest(SearchUtilsMixin):
    def setUp(self):
        self.create_search_index(
            Article,
            "autocomplete_headline_index",
            {
                "mappings": {
                    "dynamic": False,
                    "fields": {
                        "headline": {
                            "type": "autocomplete",
                            "analyzer": "lucene.standard",
                            "tokenization": "edgeGram",
                            "minGrams": 3,
                            "maxGrams": 5,
                            "foldDiacritics": False,
                        }
                    },
                }
            },
        )
        self.article = Article.objects.create(
            headline="crossing and something", number=2, body="river"
        )
        Article.objects.create(headline="Some random text", number=3, body="river")

    def tearDown(self):
        self._tear_down(Article)
        super().tearDown()

    def test_search_autocomplete(self):
        qs = Article.objects.annotate(score=SearchAutocomplete(path="headline", query="crossing"))
        self.wait_for_assertion(lambda: self.assertCountEqual(qs.all(), [self.article]))


class SearchExistsTest(SearchUtilsMixin):
    def setUp(self):
        self.create_search_index(
            Article,
            "exists_body_index",
            {"mappings": {"dynamic": False, "fields": {"body": {"type": "token"}}}},
        )
        self.article = Article.objects.create(headline="ignored", number=3, body="something")

    def test_search_exists(self):
        qs = Article.objects.annotate(score=SearchExists(path="body"))
        self.wait_for_assertion(lambda: self.assertCountEqual(qs.all(), [self.article]))


class SearchInTest(SearchUtilsMixin):
    def setUp(self):
        self.create_search_index(
            Article,
            "in_headline_index",
            {"mappings": {"dynamic": False, "fields": {"headline": {"type": "token"}}}},
        )
        self.article = Article.objects.create(headline="cross", number=1, body="a")
        Article.objects.create(headline="road", number=2, body="b")

    def tearDown(self):
        self._tear_down(Article)
        super().tearDown()

    def test_search_in(self):
        qs = Article.objects.annotate(score=SearchIn(path="headline", value=["cross", "river"]))
        self.wait_for_assertion(lambda: self.assertCountEqual(qs.all(), [self.article]))


class SearchPhraseTest(SearchUtilsMixin):
    def setUp(self):
        self.create_search_index(
            Article,
            "phrase_body_index",
            {"mappings": {"dynamic": False, "fields": {"body": {"type": "string"}}}},
        )
        self.article = Article.objects.create(
            headline="irrelevant", number=1, body="the quick brown fox"
        )
        Article.objects.create(headline="cheetah", number=2, body="fastest animal")

    def tearDown(self):
        self._tear_down(Article)
        super().tearDown()

    def test_search_phrase(self):
        qs = Article.objects.annotate(score=SearchPhrase(path="body", query="quick brown"))
        self.wait_for_assertion(lambda: self.assertCountEqual(qs.all(), [self.article]))


class SearchRangeTest(SearchUtilsMixin):
    def setUp(self):
        self.create_search_index(
            Article,
            "range_number_index",
            {"mappings": {"dynamic": False, "fields": {"number": {"type": "number"}}}},
        )
        Article.objects.create(headline="x", number=5, body="z")
        self.number20 = Article.objects.create(headline="y", number=20, body="z")

    def tearDown(self):
        self._tear_down(Article)
        super().tearDown()

    def test_search_range(self):
        qs = Article.objects.annotate(score=SearchRange(path="number", gte=10, lt=30))
        self.wait_for_assertion(lambda: self.assertCountEqual(qs.all(), [self.number20]))


class SearchRegexTest(SearchUtilsMixin):
    def setUp(self):
        self.create_search_index(
            Article,
            "regex_headline_index",
            {
                "mappings": {
                    "dynamic": False,
                    "fields": {"headline": {"type": "string", "analyzer": "lucene.keyword"}},
                }
            },
        )
        self.article = Article.objects.create(headline="hello world", number=1, body="abc")
        Article.objects.create(headline="hola mundo", number=2, body="abc")

    def tearDown(self):
        self._tear_down(Article)
        super().tearDown()

    def test_search_regex(self):
        qs = Article.objects.annotate(
            score=SearchRegex(path="headline", query="hello.*", allow_analyzed_field=True)
        )
        self.wait_for_assertion(lambda: self.assertCountEqual(qs.all(), [self.article]))


class SearchTextTest(SearchUtilsMixin):
    def setUp(self):
        self.create_search_index(
            Article,
            "text_body_index",
            {"mappings": {"dynamic": False, "fields": {"body": {"type": "string"}}}},
        )
        self.article = Article.objects.create(
            headline="ignored", number=1, body="The lazy dog sleeps"
        )
        Article.objects.create(headline="ignored", number=2, body="The sleepy bear")

    def tearDown(self):
        self._tear_down(Article)
        super().tearDown()

    def test_search_text(self):
        qs = Article.objects.annotate(score=SearchText(path="body", query="lazy"))
        self.wait_for_assertion(lambda: self.assertCountEqual([self.article], qs))

    def test_search_text_with_fuzzy_and_criteria(self):
        qs = Article.objects.annotate(
            score=SearchText(
                path="body", query="lazzy", fuzzy={"maxEdits": 2}, match_criteria="all"
            )
        )
        self.wait_for_assertion(lambda: self.assertCountEqual(qs.all(), [self.article]))


class SearchWildcardTest(SearchUtilsMixin):
    def setUp(self):
        self.create_search_index(
            Article,
            "wildcard_headline_index",
            {
                "mappings": {
                    "dynamic": False,
                    "fields": {"headline": {"type": "string", "analyzer": "lucene.keyword"}},
                }
            },
        )
        self.article = Article.objects.create(headline="dark-knight", number=1, body="")
        Article.objects.create(headline="batman", number=2, body="")

    def tearDown(self):
        self._tear_down(Article)
        super().tearDown()

    def test_search_wildcard(self):
        qs = Article.objects.annotate(score=SearchWildcard(path="headline", query="dark-*"))
        self.wait_for_assertion(lambda: self.assertCountEqual([self.article], qs))


class SearchGeoShapeTest(SearchUtilsMixin):
    def setUp(self):
        self.create_search_index(
            Article,
            "geoshape_location_index",
            {
                "mappings": {
                    "dynamic": False,
                    "fields": {"location": {"type": "geo", "indexShapes": True}},
                }
            },
        )
        self.article = Article.objects.create(
            headline="any", number=1, body="", location={"type": "Point", "coordinates": [40, 5]}
        )
        Article.objects.create(
            headline="any", number=2, body="", location={"type": "Point", "coordinates": [400, 50]}
        )

    def tearDown(self):
        self._tear_down(Article)
        super().tearDown()

    def test_search_geo_shape(self):
        polygon = {
            "type": "Polygon",
            "coordinates": [[[30, 0], [50, 0], [50, 10], [30, 10], [30, 0]]],
        }
        qs = Article.objects.annotate(
            score=SearchGeoShape(path="location", relation="within", geometry=polygon)
        )
        self.wait_for_assertion(lambda: self.assertCountEqual(qs.all(), [self.article]))


class SearchGeoWithinTest(SearchUtilsMixin):
    def setUp(self):
        self.create_search_index(
            Article,
            "geowithin_location_index",
            {"mappings": {"dynamic": False, "fields": {"location": {"type": "geo"}}}},
        )
        self.article = Article.objects.create(
            headline="geo", number=2, body="", location={"type": "Point", "coordinates": [40, 5]}
        )
        Article.objects.create(
            headline="geo2", number=3, body="", location={"type": "Point", "coordinates": [-40, -5]}
        )

    def tearDown(self):
        self._tear_down(Article)
        super().tearDown()

    def test_search_geo_within(self):
        polygon = {
            "type": "Polygon",
            "coordinates": [[[30, 0], [50, 0], [50, 10], [30, 10], [30, 0]]],
        }
        qs = Article.objects.annotate(
            score=SearchGeoWithin(
                path="location",
                kind="geometry",
                geo_object=polygon,
            )
        )
        self.wait_for_assertion(lambda: self.assertCountEqual(qs.all(), [self.article]))


@unittest.expectedFailure
class SearchMoreLikeThisTest(SearchUtilsMixin):
    def setUp(self):
        self.create_search_index(
            Article,
            "mlt_index",
            {
                "mappings": {
                    "dynamic": False,
                    "fields": {"body": {"type": "string"}, "headline": {"type": "string"}},
                }
            },
        )
        self.article1 = Article.objects.create(
            headline="Space exploration", number=1, body="Webb telescope"
        )
        self.article2 = Article.objects.create(
            headline="The commodities fall",
            number=2,
            body="Commodities dropped sharply due to inflation concerns",
        )
        Article.objects.create(
            headline="irrelevant",
            number=3,
            body="This is a completely unrelated article about cooking",
        )

    def tearDown(self):
        self._tear_down(Article)
        super().tearDown()

    def test_search_more_like_this(self):
        like_docs = [
            {"headline": self.article1.headline, "body": self.article1.body},
            {"headline": self.article2.headline, "body": self.article2.body},
        ]
        like_docs = [{"body": "NASA launches new satellite to explore the galaxy"}]
        qs = Article.objects.annotate(score=SearchMoreLikeThis(documents=like_docs)).order_by(
            "score"
        )
        self.wait_for_assertion(
            lambda: self.assertQuerySetEqual(
                qs.all(), [self.article1, self.article2], lambda a: a.headline
            )
        )


class CompoundSearchTest(SearchUtilsMixin):
    def setUp(self):
        self.create_search_index(
            Article,
            "compound_index",
            {
                "mappings": {
                    "dynamic": False,
                    "fields": {
                        "headline": {"type": "token"},
                        "body": {"type": "string"},
                        "number": {"type": "number"},
                    },
                }
            },
        )
        self.mars_mission = Article.objects.create(
            number=1,
            headline="space exploration",
            body="NASA launches a new mission to Mars, aiming to study surface geology",
        )

        self.exoplanet = Article.objects.create(
            number=2,
            headline="space exploration",
            body="Astronomers discover exoplanets orbiting distant stars using Webb telescope",
        )

        self.icy_moons = Article.objects.create(
            number=3,
            headline="space exploration",
            body="ESA prepares a robotic expedition to explore the icy moons of Jupiter",
        )

        self.comodities_drop = Article.objects.create(
            number=4,
            headline="astronomy news",
            body="Commodities dropped sharply due to inflation concerns",
        )

    def tearDown(self):
        self._tear_down(Article)
        super().tearDown()

    def test_compound_expression(self):
        must_expr = SearchEquals(path="headline", value="space exploration")
        must_not_expr = SearchPhrase(path="body", query="icy moons")
        should_expr = SearchPhrase(path="body", query="exoplanets")

        compound = CompoundExpression(
            must=[must_expr or should_expr],
            must_not=[must_not_expr],
            should=[should_expr],
            minimum_should_match=1,
        )

        qs = Article.objects.annotate(score=compound).order_by("score")
        self.wait_for_assertion(lambda: self.assertCountEqual(qs.all(), [self.exoplanet]))

    def test_compound_operations(self):
        expr = SearchEquals(path="headline", value="space exploration") & ~SearchEquals(
            path="number", value=3
        )
        qs = Article.objects.annotate(score=expr)
        self.wait_for_assertion(
            lambda: self.assertCountEqual(qs.all(), [self.mars_mission, self.exoplanet])
        )


class SearchVectorTest(SearchUtilsMixin):
    def setUp(self):
        self.create_search_index(
            Article,
            "vector_index",
            {
                "fields": [
                    {
                        "type": "vector",
                        "path": "plot_embedding",
                        "numDimensions": 3,
                        "similarity": "cosine",
                        "quantization": "scalar",
                    }
                ]
            },
            type="vectorSearch",
        )

        self.mars = Article.objects.create(
            headline="Mars landing",
            number=1,
            body="The rover has landed on Mars",
            plot_embedding=[0.1, 0.2, 0.3],
        )
        self.cooking = Article.objects.create(
            headline="Cooking tips",
            number=2,
            body="This article is about pasta",
            plot_embedding=[0.9, 0.8, 0.7],
        )

    def tearDown(self):
        self._tear_down(Article)
        super().tearDown()

    def test_vector_search(self):
        vector_query = [0.1, 0.2, 0.3]
        expr = SearchVector(
            path="plot_embedding",
            query_vector=vector_query,
            num_candidates=5,
            limit=2,
        )
        qs = Article.objects.annotate(score=expr).order_by("-score")
        self.wait_for_assertion(lambda: self.assertCountEqual(qs.all(), [self.mars, self.cooking]))
