import unittest
from collections.abc import Callable
from functools import wraps
from time import monotonic, sleep

from django.db import connection
from django.db.models import Q
from django.db.models.query import QuerySet
from django.db.utils import DatabaseError
from django.test import TransactionTestCase, skipUnlessDBFeature
from pymongo.operations import SearchIndexModel

from django_mongodb_backend.expressions import (
    CompoundExpression,
    SearchAutocomplete,
    SearchEquals,
    SearchExists,
    SearchGeoShape,
    SearchGeoWithin,
    SearchIn,
    SearchMoreLikeThis,
    SearchPhrase,
    SearchQueryString,
    SearchRange,
    SearchRegex,
    SearchScoreOption,
    SearchText,
    SearchVector,
    SearchWildcard,
)

from .models import Article, Location, Writer


def wait_until_index_ready(collection, index_name, timeout: float = 5, interval: float = 0.5):
    start = monotonic()
    while monotonic() - start < timeout:
        indexes = list(collection.list_search_indexes())
        for idx in indexes:
            if idx["name"] == index_name and idx["status"] == "READY":
                return True
        sleep(interval)
    raise TimeoutError(f"Index {index_name} not ready after {timeout} seconds")


def _delayed_assertion(timeout: float = 4, interval: float = 0.5):
    def decorator(assert_func):
        @wraps(assert_func)
        def wrapper(self, fetch, *args, **kwargs):
            start = monotonic()
            if not isinstance(fetch, Callable | QuerySet):
                raise ValueError(
                    "The first argument to a delayed assertion must be a QuerySet or a callable "
                    "that returns the value to be asserted."
                )
            if isinstance(fetch, QuerySet):
                fetch = fetch.all
            while True:
                try:
                    return assert_func(self, fetch(), *args, **kwargs)
                except (AssertionError, DatabaseError):
                    if monotonic() - start > timeout:
                        raise
                    sleep(interval)

        wrapper.__name__ = f"delayed{assert_func.__name__.title()}"
        return wrapper

    return decorator


@skipUnlessDBFeature("supports_atlas_search")
class SearchUtilsMixin(TransactionTestCase):
    available_apps = None

    """
    These assertions include a small delay to account for MongoDB Atlas Search's
    eventual consistency and indexing latency. Data inserted into MongoDB is not
    immediately available for $search queries because Atlas Search indexes are
    updated asynchronously via change streams. While this is usually fast, delays
    can occur due to replication lag, system load, index complexity, or a high
    number of search indexes.
    """
    assertCountEqual = _delayed_assertion(timeout=2)(TransactionTestCase.assertCountEqual)
    assertListEqual = _delayed_assertion(timeout=2)(TransactionTestCase.assertListEqual)
    assertQuerySetEqual = _delayed_assertion(timeout=2)(TransactionTestCase.assertQuerySetEqual)

    @staticmethod
    def _get_collection(model):
        return connection.database.get_collection(model._meta.db_table)

    @classmethod
    def create_search_index(cls, model, index_name, definition, type="search"):
        collection = cls._get_collection(model)
        idx = SearchIndexModel(definition=definition, name=index_name, type=type)
        collection.create_search_index(idx)
        wait_until_index_ready(collection, index_name)

        def drop_index():
            collection.drop_search_index(index_name)

        cls.addClassCleanup(drop_index)


class SearchEqualsTests(SearchUtilsMixin):
    @classmethod
    def setUpClass(cls):
        cls.create_search_index(
            Article,
            "equals_headline_index",
            {
                "mappings": {
                    "dynamic": False,
                    "fields": {"headline": {"type": "token"}, "number": {"type": "number"}},
                }
            },
        )

    def setUp(self):
        self.article = Article.objects.create(headline="cross", number=1, body="body")
        Article.objects.create(headline="other thing", number=2, body="body")

    def test_search_equals(self):
        qs = Article.objects.annotate(score=SearchEquals(path="headline", value="cross"))
        self.assertCountEqual(qs, [self.article])

    def test_boost_score(self):
        boost_score = SearchScoreOption({"boost": {"value": 3}})
        qs = Article.objects.annotate(
            score=SearchEquals(path="headline", value="cross", score=boost_score)
        )
        self.assertCountEqual(qs, [self.article])
        scored = qs.first()
        self.assertGreaterEqual(scored.score, 3.0)

    def test_constant_score(self):
        constant_score = SearchScoreOption({"constant": {"value": 10}})
        qs = Article.objects.annotate(
            score=SearchEquals(path="headline", value="cross", score=constant_score)
        )
        self.assertCountEqual(qs, [self.article])
        scored = qs.first()
        self.assertAlmostEqual(scored.score, 10.0, places=2)

    def test_function_score(self):
        function_score = SearchScoreOption(
            {
                "function": {
                    "path": {
                        "value": "number",
                        "undefined": 0,
                    },
                }
            }
        )

        qs = Article.objects.annotate(
            score=SearchEquals(path="headline", value="cross", score=function_score)
        )
        self.assertCountEqual(qs, [self.article])
        scored = qs.first()
        self.assertAlmostEqual(scored.score, 1.0, places=2)

    def test_str_returns_expected_format(self):
        score = SearchScoreOption({"constant": {"value": 10}})
        se = SearchEquals(path="headline", value="cross", score=score)
        self.assertEqual(str(se), f"<SearchEquals(path='headline', value='cross', score={score})>")


class SearchAutocompleteTests(SearchUtilsMixin):
    @classmethod
    def setUpClass(cls):
        cls.create_search_index(
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
                        },
                        "writer": {
                            "type": "document",
                            "fields": {
                                "name": {
                                    "type": "autocomplete",
                                    "analyzer": "lucene.standard",
                                    "tokenization": "edgeGram",
                                    "minGrams": 3,
                                    "maxGrams": 5,
                                    "foldDiacritics": False,
                                }
                            },
                        },
                    },
                }
            },
        )

    def setUp(self):
        self.article = Article.objects.create(
            headline="crossing and something",
            number=2,
            body="river",
            writer=Writer(name="Joselina A. Ramirez"),
        )
        Article.objects.create(headline="Some random text", number=3, body="river")

    def test_search_autocomplete(self):
        qs = Article.objects.annotate(
            score=SearchAutocomplete(
                path="headline",
                query="crossing",
                token_order="sequential",  # noqa: S106
                fuzzy={"maxEdits": 2},
            )
        )
        self.assertCountEqual(qs, [self.article])

    def test_search_autocomplete_embedded_model(self):
        qs = Article.objects.annotate(
            score=SearchAutocomplete(path="writer__name", query="Joselina")
        )
        self.assertCountEqual(qs, [self.article])

    def test_constant_score(self):
        constant_score = SearchScoreOption({"constant": {"value": 10}})
        qs = Article.objects.annotate(
            score=SearchAutocomplete(
                path="headline",
                query="crossing",
                token_order="sequential",  # noqa: S106
                fuzzy={"maxEdits": 2},
                score=constant_score,
            )
        )
        self.assertCountEqual(qs, [self.article])
        scored = qs.first()
        self.assertAlmostEqual(scored.score, 10.0, places=2)

    def test_str_returns_expected_format(self):
        score = SearchScoreOption({"constant": {"value": 10}})
        se = SearchAutocomplete(path="writer__name", query="Joselina", score=score)
        self.assertEqual(
            str(se),
            "<SearchAutocomplete(path='writer__name', query='Joselina', fuzzy=None,"
            f" token_order=None, score={score})>",
        )


class SearchExistsTests(SearchUtilsMixin):
    @classmethod
    def setUpClass(cls):
        cls.create_search_index(
            Article,
            "exists_body_index",
            {"mappings": {"dynamic": False, "fields": {"body": {"type": "token"}}}},
        )

    def setUp(self):
        self.article = Article.objects.create(headline="ignored", number=3, body="something")

    def test_search_exists(self):
        qs = Article.objects.annotate(score=SearchExists(path="body"))
        self.assertCountEqual(qs, [self.article])

    def test_constant_score(self):
        constant_score = SearchScoreOption({"constant": {"value": 10}})
        qs = Article.objects.annotate(score=SearchExists(path="body", score=constant_score))
        self.assertCountEqual(qs, [self.article])
        scored = qs.first()
        self.assertAlmostEqual(scored.score, 10.0, places=2)

    def test_str_returns_expected_format(self):
        score = SearchScoreOption({"constant": {"value": 10}})
        se = SearchExists(path="body", score=score)
        self.assertEqual(str(se), f"<SearchExists(path='body', score={score})>")


class SearchInTests(SearchUtilsMixin):
    @classmethod
    def setUpClass(cls):
        cls.create_search_index(
            Article,
            "in_headline_index",
            {"mappings": {"dynamic": False, "fields": {"headline": {"type": "token"}}}},
        )

    def setUp(self):
        self.article = Article.objects.create(headline="cross", number=1, body="a")
        Article.objects.create(headline="road", number=2, body="b")

    def test_search_in(self):
        qs = Article.objects.annotate(score=SearchIn(path="headline", value=["cross", "river"]))
        self.assertCountEqual(qs, [self.article])

    def test_constant_score(self):
        constant_score = SearchScoreOption({"constant": {"value": 10}})
        qs = Article.objects.annotate(
            score=SearchIn(path="headline", value=["cross", "river"], score=constant_score)
        )
        self.assertCountEqual(qs, [self.article])
        scored = qs.first()
        self.assertAlmostEqual(scored.score, 10.0, places=2)

    def test_str_returns_expected_format(self):
        score = SearchScoreOption({"constant": {"value": 10}})
        se = SearchIn(path="headline", value=["cross", "river"], score=score)
        self.assertEqual(
            str(se), f"<SearchIn(path='headline', value=('cross', 'river'), score={score})>"
        )


class SearchPhraseTests(SearchUtilsMixin):
    @classmethod
    def setUpClass(cls):
        cls.create_search_index(
            Article,
            "phrase_body_index",
            {"mappings": {"dynamic": False, "fields": {"body": {"type": "string"}}}},
        )

    def setUp(self):
        self.article = Article.objects.create(
            headline="irrelevant", number=1, body="the quick brown fox"
        )
        Article.objects.create(headline="cheetah", number=2, body="fastest animal")

    def test_search_phrase(self):
        qs = Article.objects.annotate(score=SearchPhrase(path="body", query="quick brown", slop=3))
        self.assertCountEqual(qs, [self.article])

    def test_constant_score(self):
        constant_score = SearchScoreOption({"constant": {"value": 10}})
        qs = Article.objects.annotate(
            score=SearchPhrase(path="body", query="quick brown", score=constant_score)
        )
        self.assertCountEqual(qs, [self.article])
        scored = qs.first()
        self.assertAlmostEqual(scored.score, 10.0, places=2)

    def test_str_returns_expected_format(self):
        score = SearchScoreOption({"constant": {"value": 10}})
        se = SearchPhrase(path="body", query="quick brown", score=score)
        self.assertEqual(
            str(se),
            "<SearchPhrase(path='body', query='quick brown', slop=None, "
            f"synonyms=None, score={score})>",
        )


@skipUnlessDBFeature("supports_atlas_search")
class SearchQueryStringTests(SearchUtilsMixin):
    @classmethod
    def setUpClass(cls):
        cls.create_search_index(
            Article,
            "query_string_index",
            {
                "mappings": {
                    "dynamic": False,
                    "fields": {
                        "headline": {"type": "string"},
                        "body": {"type": "string"},
                    },
                }
            },
        )

    def setUp(self):
        self.mars_mission = Article.objects.create(
            headline="space exploration",
            body="NASA launches a new mission to Mars",
            number=1,
        )
        self.exoplanet = Article.objects.create(
            headline="space exploration",
            body="Astronomers discover exoplanets orbiting distant stars",
            number=2,
        )
        Article.objects.create(
            headline="other news",
            body="Local team wins championship",
            number=3,
        )

    def test_search_query_string_basic(self):
        qs = Article.objects.annotate(
            score=SearchQueryString(path="headline", query="space AND body:Mars")
        )
        self.assertCountEqual(qs, [self.mars_mission])

    def test_search_query_string_with_score(self):
        constant_score = SearchScoreOption({"constant": {"value": 10}})
        qs = Article.objects.annotate(
            score=SearchQueryString(
                path="headline",
                query="space AND body:exoplanets",
                score=constant_score,
            )
        )
        self.assertCountEqual(qs, [self.exoplanet])
        self.assertAlmostEqual(qs.first().score, 10.0, places=2)

    def test_str_returns_expected_format(self):
        score = SearchScoreOption({"constant": {"value": 10}})
        se = SearchQueryString(path="body", query="space AND body:exoplanets", score=score)
        self.assertEqual(
            str(se),
            f"<SearchQueryString(path='body', query='space AND body:exoplanets', score={score})>",
        )


class SearchRangeTests(SearchUtilsMixin):
    @classmethod
    def setUpClass(cls):
        cls.create_search_index(
            Article,
            "range_number_index",
            {"mappings": {"dynamic": False, "fields": {"number": {"type": "number"}}}},
        )
        Article.objects.create(headline="x", number=5, body="z")

    def setUp(self):
        self.number20 = Article.objects.create(headline="y", number=20, body="z")

    def test_search_range(self):
        qs = Article.objects.annotate(score=SearchRange(path="number", gte=10, lt=30))
        self.assertCountEqual(qs, [self.number20])
        qs = Article.objects.annotate(score=SearchRange(path="number", gt=20, lte=30))
        self.assertCountEqual(qs, [])

    def test_constant_score(self):
        constant_score = SearchScoreOption({"constant": {"value": 10}})
        qs = Article.objects.annotate(
            score=SearchRange(path="number", gte=10, lt=30, score=constant_score)
        )
        self.assertCountEqual(qs, [self.number20])
        scored = qs.first()
        self.assertAlmostEqual(scored.score, 10.0, places=2)

    def test_str_returns_expected_format(self):
        score = SearchScoreOption({"constant": {"value": 10}})
        se = SearchRange(path="number", gte=10, lt=30, score=score)
        self.assertEqual(
            str(se),
            f"<SearchRange(path='number', lt=30, lte=None, gt=None, gte=10, score={score})>",
        )


class SearchRegexTests(SearchUtilsMixin):
    @classmethod
    def setUpClass(cls):
        cls.create_search_index(
            Article,
            "regex_headline_index",
            {
                "mappings": {
                    "dynamic": False,
                    "fields": {"headline": {"type": "string", "analyzer": "lucene.keyword"}},
                }
            },
        )

    def setUp(self):
        self.article = Article.objects.create(headline="hello world", number=1, body="abc")
        Article.objects.create(headline="hola mundo", number=2, body="abc")

    def test_search_regex(self):
        qs = Article.objects.annotate(
            score=SearchRegex(path="headline", query="hello.*", allow_analyzed_field=True)
        )
        self.assertCountEqual(qs, [self.article])

    def test_constant_score(self):
        constant_score = SearchScoreOption({"constant": {"value": 10}})
        qs = Article.objects.annotate(
            score=SearchRegex(
                path="headline", query="hello.*", allow_analyzed_field=True, score=constant_score
            )
        )
        self.assertCountEqual(qs, [self.article])
        scored = qs.first()
        self.assertAlmostEqual(scored.score, 10.0, places=2)

    def test_str_returns_expected_format(self):
        score = SearchScoreOption({"constant": {"value": 10}})
        se = SearchRegex(path="headline", query="hello.*", allow_analyzed_field=True, score=score)
        self.assertEqual(
            str(se),
            "<SearchRegex(path='headline', query='hello.*', "
            f"allow_analyzed_field=True, score={score})>",
        )


class SearchTextTests(SearchUtilsMixin):
    @classmethod
    def setUpClass(cls):
        cls.create_search_index(
            Article,
            "text_body_index",
            {"mappings": {"dynamic": False, "fields": {"body": {"type": "string"}}}},
        )

    def setUp(self):
        self.article = Article.objects.create(
            headline="ignored", number=1, body="The lazy dog sleeps"
        )
        Article.objects.create(headline="ignored", number=2, body="The sleepy bear")

    def test_search_text(self):
        qs = Article.objects.annotate(score=SearchText(path="body", query="lazy"))
        self.assertCountEqual(qs, [self.article])

    def test_search_lookup(self):
        qs = Article.objects.filter(body__search="lazy")
        self.assertCountEqual(qs, [self.article])

    def test_search_text_with_fuzzy_and_criteria(self):
        qs = Article.objects.annotate(
            score=SearchText(
                path="body", query="lazzy", fuzzy={"maxEdits": 2}, match_criteria="all"
            )
        )
        self.assertCountEqual(qs, [self.article])

    def test_constant_score(self):
        constant_score = SearchScoreOption({"constant": {"value": 10}})
        qs = Article.objects.annotate(
            score=SearchText(
                path="body",
                query="lazzy",
                fuzzy={"maxEdits": 2},
                match_criteria="all",
                score=constant_score,
            )
        )
        self.assertCountEqual(qs, [self.article])
        scored = qs.first()
        self.assertAlmostEqual(scored.score, 10.0, places=2)

    def test_str_returns_expected_format(self):
        score = SearchScoreOption({"constant": {"value": 10}})
        se = SearchText(
            path="body",
            query="lazzy",
            fuzzy={"maxEdits": 2},
            match_criteria="all",
            score=score,
        )
        self.assertEqual(
            str(se),
            "<SearchText(path='body', query='lazzy', fuzzy=(('maxEdits', 2),), "
            f"match_criteria='all', synonyms=None, score={score})>",
        )


class SearchWildcardTests(SearchUtilsMixin):
    @classmethod
    def setUpClass(cls):
        cls.create_search_index(
            Article,
            "wildcard_headline_index",
            {
                "mappings": {
                    "dynamic": False,
                    "fields": {"headline": {"type": "string", "analyzer": "lucene.keyword"}},
                }
            },
        )

    def setUp(self):
        self.article = Article.objects.create(headline="dark-knight", number=1, body="")
        Article.objects.create(headline="batman", number=2, body="")

    def test_search_wildcard(self):
        qs = Article.objects.annotate(
            score=SearchWildcard(path="headline", query="dark-*", allow_analyzed_field=False)
        )
        self.assertCountEqual(qs, [self.article])

    def test_constant_score(self):
        constant_score = SearchScoreOption({"constant": {"value": 10}})
        qs = Article.objects.annotate(
            score=SearchWildcard(path="headline", query="dark-*", score=constant_score)
        )
        self.assertCountEqual(qs, [self.article])
        scored = qs.first()
        self.assertAlmostEqual(scored.score, 10.0, places=2)

    def test_str_returns_expected_format(self):
        score = SearchScoreOption({"constant": {"value": 10}})
        se = SearchWildcard(path="headline", query="dark-*", score=score)
        self.assertEqual(
            str(se),
            "<SearchWildcard(path='headline', query='dark-*', "
            f"allow_analyzed_field=None, score={score})>",
        )


class SearchGeoShapeTests(SearchUtilsMixin):
    @classmethod
    def setUpClass(cls):
        cls.create_search_index(
            Article,
            "geoshape_location_index",
            {
                "mappings": {
                    "dynamic": False,
                    "fields": {"location": {"type": "geo", "indexShapes": True}},
                }
            },
        )

    def setUp(self):
        self.article = Article.objects.create(
            headline="any", number=1, body="", location=Location(type="Point", coordinates=[40, 5])
        )
        Article.objects.create(
            headline="any",
            number=2,
            body="",
            location=Location(type="Point", coordinates=[400, 50]),
        )

    def test_search_geo_shape(self):
        polygon = {
            "type": "Polygon",
            "coordinates": [[[30, 0], [50, 0], [50, 10], [30, 10], [30, 0]]],
        }
        qs = Article.objects.annotate(
            score=SearchGeoShape(path="location", relation="within", geometry=polygon)
        )
        self.assertCountEqual(qs, [self.article])

    def test_constant_score(self):
        polygon = {
            "type": "Polygon",
            "coordinates": [[[30, 0], [50, 0], [50, 10], [30, 10], [30, 0]]],
        }
        constant_score = SearchScoreOption({"constant": {"value": 10}})
        qs = Article.objects.annotate(
            score=SearchGeoShape(
                path="location", relation="within", geometry=polygon, score=constant_score
            )
        )
        self.assertCountEqual(qs, [self.article])
        scored = qs.first()
        self.assertAlmostEqual(scored.score, 10.0, places=2)

    def test_str_returns_expected_format(self):
        score = SearchScoreOption({"constant": {"value": 10}})
        polygon = {
            "type": "Polygon",
            "coordinates": [[[30, 0], [50, 0], [50, 10], [30, 10], [30, 0]]],
        }
        se = SearchGeoShape(path="location", relation="within", geometry=polygon, score=score)
        self.assertEqual(
            str(se),
            "<SearchGeoShape(path='location', relation='within', geometry=(('type', 'Polygon'), "
            "('coordinates', (((30, 0), (50, 0), (50, 10), (30, 10), (30, 0)),))), "
            f"score={score})>",
        )


class SearchGeoWithinTests(SearchUtilsMixin):
    @classmethod
    def setUpClass(cls):
        cls.create_search_index(
            Article,
            "geowithin_location_index",
            {"mappings": {"dynamic": False, "fields": {"location": {"type": "geo"}}}},
        )

    def setUp(self):
        self.article = Article.objects.create(
            headline="geo", number=2, body="", location=Location(type="Point", coordinates=[40, 5])
        )
        Article.objects.create(
            headline="geo2",
            number=3,
            body="",
            location=Location(type="Point", coordinates=[-40, -5]),
        )

    def test_search_geo_within(self):
        polygon = {
            "type": "Polygon",
            "coordinates": [[[30, 0], [50, 0], [50, 10], [30, 10], [30, 0]]],
        }
        qs = Article.objects.annotate(
            score=SearchGeoWithin(
                path="location",
                kind="geometry",
                geometry=polygon,
            )
        )
        self.assertCountEqual(qs, [self.article])

    def test_constant_score(self):
        polygon = {
            "type": "Polygon",
            "coordinates": [[[30, 0], [50, 0], [50, 10], [30, 10], [30, 0]]],
        }
        constant_score = SearchScoreOption({"constant": {"value": 10}})
        qs = Article.objects.annotate(
            score=SearchGeoWithin(
                path="location",
                kind="geometry",
                geometry=polygon,
                score=constant_score,
            )
        )
        self.assertCountEqual(qs, [self.article])
        scored = qs.first()
        self.assertAlmostEqual(scored.score, 10.0, places=2)

    def test_str_returns_expected_format(self):
        score = SearchScoreOption({"constant": {"value": 10}})
        polygon = {
            "type": "Polygon",
            "coordinates": [[[30, 0], [50, 0], [50, 10], [30, 10], [30, 0]]],
        }
        se = SearchGeoWithin(
            path="location",
            kind="geometry",
            geometry=polygon,
            score=score,
        )
        self.assertEqual(
            str(se),
            "<SearchGeoWithin(path='location', kind='geometry', geometry=(('type', 'Polygon'), "
            "('coordinates', (((30, 0), (50, 0), (50, 10), (30, 10), (30, 0)),))), "
            f"score={score})>",
        )


@unittest.expectedFailure
class SearchMoreLikeThisTests(SearchUtilsMixin):
    """Expected failure: Cannot find a matching document in search index."""

    @classmethod
    def setUpClass(cls):
        cls.create_search_index(
            Article,
            "mlt_index",
            {
                "mappings": {
                    "dynamic": False,
                    "fields": {"body": {"type": "string"}, "headline": {"type": "string"}},
                }
            },
        )
        cls.article1 = Article.objects.create(
            headline="Space exploration", number=1, body="Webb telescope"
        )
        cls.article2 = Article.objects.create(
            headline="The commodities fall",
            number=2,
            body="Commodities dropped sharply due to inflation concerns",
        )
        Article.objects.create(
            headline="irrelevant",
            number=3,
            body="This is a completely unrelated article about cooking",
        )

    def test_search_more_like_this(self):
        like_docs = [
            {"headline": self.article1.headline, "body": self.article1.body},
            {"headline": self.article2.headline, "body": self.article2.body},
        ]
        qs = Article.objects.annotate(score=SearchMoreLikeThis(documents=like_docs)).order_by(
            "score"
        )
        self.assertQuerySetEqual(qs, [self.article1, self.article2], lambda a: a.headline)


class CompoundSearchTests(SearchUtilsMixin):
    @classmethod
    def setUpClass(cls):
        cls.create_search_index(
            Article,
            "compound_index",
            {
                "mappings": {
                    "dynamic": False,
                    "fields": {
                        "headline": [{"type": "token"}, {"type": "string"}],
                        "body": {"type": "string"},
                        "number": {"type": "number"},
                    },
                }
            },
        )

    def setUp(self):
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

    def test_expression(self):
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
        self.assertCountEqual(qs, [self.exoplanet])

    def test_operations(self):
        expr = SearchEquals(path="headline", value="space exploration") & ~SearchEquals(
            path="number", value=3
        )
        qs = Article.objects.annotate(score=expr)
        self.assertCountEqual(qs, [self.mars_mission, self.exoplanet])

    def test_mixed_scores(self):
        boost_score = SearchScoreOption({"boost": {"value": 5}})
        constant_score = SearchScoreOption({"constant": {"value": 20}})
        function_score = SearchScoreOption(
            {"function": {"path": {"value": "number", "undefined": 0}}}
        )

        must_expr = SearchEquals(path="headline", value="space exploration", score=boost_score)
        should_expr = SearchPhrase(path="body", query="exoplanets", score=constant_score)
        must_not_expr = SearchPhrase(path="body", query="icy moons", score=function_score)
        filter_ = SearchRange(path="number", gte=1, lt=4)

        compound = CompoundExpression(
            must=[must_expr],
            must_not=[must_not_expr],
            should=[should_expr],
            filter=[filter_],
        )
        qs = Article.objects.annotate(score=compound).order_by("-score")
        self.assertListEqual(lambda: list(qs.all()), [self.exoplanet, self.mars_mission])
        # Exoplanet should rank first because of the constant 20 bump.
        self.assertEqual(qs.first(), self.exoplanet)

    def test_operationss_with_function_score(self):
        function_score = SearchScoreOption(
            {"function": {"path": {"value": "number", "undefined": 0}}}
        )

        expr = SearchEquals(
            path="headline",
            value="space exploration",
            score=function_score,
        ) & ~SearchEquals(path="number", value=3)

        qs = Article.objects.annotate(score=expr).order_by("-score")
        self.assertListEqual(lambda: list(qs.all()), [self.exoplanet, self.mars_mission])
        # Returns mars_mission (score≈1) and exoplanet (score≈2) then; exoplanet first.
        self.assertEqual(qs.first(), self.exoplanet)

    def test_multiple_search(self):
        msg = (
            "Only one $search operation is allowed per query. Received 2 search expressions. "
            "To combine multiple search expressions, use either a CompoundExpression for "
            "fine-grained control or CombinedSearchExpression for simple logical combinations."
        )
        with self.assertRaisesMessage(ValueError, msg):
            Article.objects.annotate(
                score1=SearchEquals(path="headline", value="space exploration"),
                score2=~SearchEquals(path="number", value=3),
            ).order_by("score1", "score2").first()

        with self.assertRaisesMessage(ValueError, msg):
            Article.objects.filter(
                Q(headline__search="space exploration"), Q(headline__search="space exploration 2")
            ).first()

    def test_multiple_type_search(self):
        msg = (
            "Cannot combine a `$vectorSearch` with a `$search` operator. "
            "If you need to combine them, consider "
            "restructuring your query logic or running them as separate queries."
        )
        with self.assertRaisesMessage(ValueError, msg):
            Article.objects.annotate(
                score1=SearchEquals(path="headline", value="space exploration"),
                score2=SearchVector(
                    path="headline",
                    query_vector=[1, 2, 3],
                    num_candidates=5,
                    limit=2,
                ),
            ).order_by("score1", "score2").first()

    def test_multiple_vector_search(self):
        msg = (
            "Cannot combine two `$vectorSearch` operator. If you need to combine them, "
            "consider restructuring your query logic or running them as separate queries."
        )
        with self.assertRaisesMessage(ValueError, msg):
            Article.objects.annotate(
                score1=SearchVector(
                    path="headline",
                    query_vector=[1, 2, 3],
                    num_candidates=5,
                    limit=2,
                ),
                score2=SearchVector(
                    path="headline",
                    query_vector=[1, 2, 4],
                    num_candidates=5,
                    limit=2,
                ),
            ).order_by("score1", "score2").first()

    def test_search_and_filter(self):
        qs = Article.objects.filter(headline__search="space exploration", number__gt=2)
        self.assertCountEqual(qs, [self.icy_moons])

    def test_str_returns_expected_format(self):
        must_expr = SearchEquals(path="headline", value="space exploration")
        must_not_expr = SearchPhrase(path="body", query="icy moons")
        should_expr = SearchPhrase(path="body", query="exoplanets")

        se = CompoundExpression(
            must=[must_expr or should_expr],
            must_not=[must_not_expr],
            should=[should_expr],
            minimum_should_match=1,
        )
        self.assertEqual(
            str(se),
            "<CompoundExpression(must=(<SearchEquals(path='headline', value='space exploration', "
            "score=None)>,), must_not=(<SearchPhrase(path='body', query='icy moons', slop=None, "
            "synonyms=None, score=None)>,), should=(<SearchPhrase(path='body', "
            "query='exoplanets', slop=None, synonyms=None, score=None)>,), "
            "filter=None, score=None, minimum_should_match=1)>",
        )


class SearchVectorTests(SearchUtilsMixin):
    @classmethod
    def setUpClass(cls):
        cls.create_search_index(
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
                    },
                    {
                        "type": "filter",
                        "path": "number",
                    },
                ]
            },
            type="vectorSearch",
        )

    def setUp(self):
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
        Article.objects.create(
            headline="Local team wins championship",
            number=3,
            body="This article is about sports",
            plot_embedding=[-0.1, 0.7, 0.7],
        )

    def test_vector_search(self):
        vector_query = [0.1, 0.2, 0.3]
        expr = SearchVector(
            path="plot_embedding",
            query_vector=vector_query,
            num_candidates=5,
            limit=3,
            filter={"number": {"$lt": 3}},
            exact=False,
        )
        qs = Article.objects.annotate(score=expr).order_by("-score")
        self.assertCountEqual(qs, [self.mars, self.cooking])

    def test_str_returns_expected_format(self):
        vector_query = [0.1, 0.2, 0.3]
        se = SearchVector(
            path="plot_embedding",
            query_vector=vector_query,
            num_candidates=5,
            limit=2,
        )
        self.assertEqual(
            str(se),
            "<SearchVector(path='plot_embedding', query_vector=(0.1, 0.2, 0.3), limit=2, "
            "num_candidates=5, exact=None, filter=None)>",
        )
