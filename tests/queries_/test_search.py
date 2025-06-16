import time

from django.db import connection
from django.test import TestCase
from pymongo.operations import SearchIndexModel

from django_mongodb_backend.expressions.builtins import (
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
    SearchWildcard,
)

from .models import Article


class CreateIndexMixin:
    def _get_collection(self, model):
        return connection.database.get_collection(model._meta.db_table)

    def create_search_index(self, model, index_name, definition):
        collection = self._get_collection(model)
        idx = SearchIndexModel(definition=definition, name=index_name)
        collection.create_search_index(idx)


class SearchEqualsTest(TestCase, CreateIndexMixin):
    def setUp(self):
        self.create_search_index(
            Article,
            "equals_headline_index",
            {"mappings": {"dynamic": False, "fields": {"headline": {"type": "token"}}}},
        )
        Article.objects.create(headline="cross", number=1, body="body")
        time.sleep(1)

    def test_search_equals(self):
        qs = Article.objects.annotate(score=SearchEquals(path="headline", value="cross"))
        self.assertEqual(qs.first().headline, "cross")


class SearchAutocompleteTest(TestCase, CreateIndexMixin):
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
        Article.objects.create(headline="crossing and something", number=2, body="river")

    def test_search_autocomplete(self):
        qs = Article.objects.annotate(score=SearchAutocomplete(path="headline", query="crossing"))
        self.assertEqual(qs.first().headline, "crossing and something")


class SearchExistsTest(TestCase, CreateIndexMixin):
    def setUp(self):
        self.create_search_index(
            Article,
            "exists_body_index",
            {"mappings": {"dynamic": False, "fields": {"body": {"type": "token"}}}},
        )
        Article.objects.create(headline="ignored", number=3, body="something")

    def test_search_exists(self):
        qs = Article.objects.annotate(score=SearchExists(path="body"))
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first().body, "something")


class SearchInTest(TestCase, CreateIndexMixin):
    def setUp(self):
        self.create_search_index(
            Article,
            "in_headline_index",
            {"mappings": {"dynamic": False, "fields": {"headline": {"type": "token"}}}},
        )
        Article.objects.create(headline="cross", number=1, body="a")
        Article.objects.create(headline="road", number=2, body="b")
        time.sleep(1)

    def test_search_in(self):
        qs = Article.objects.annotate(score=SearchIn(path="headline", value=["cross", "river"]))
        self.assertEqual(qs.first().headline, "cross")


class SearchPhraseTest(TestCase, CreateIndexMixin):
    def setUp(self):
        self.create_search_index(
            Article,
            "phrase_body_index",
            {"mappings": {"dynamic": False, "fields": {"body": {"type": "string"}}}},
        )
        Article.objects.create(headline="irrelevant", number=1, body="the quick brown fox")
        time.sleep(1)

    def test_search_phrase(self):
        qs = Article.objects.annotate(score=SearchPhrase(path="body", query="quick brown"))
        self.assertIn("quick brown", qs.first().body)


class SearchRangeTest(TestCase, CreateIndexMixin):
    def setUp(self):
        self.create_search_index(
            Article,
            "range_number_index",
            {"mappings": {"dynamic": False, "fields": {"number": {"type": "number"}}}},
        )
        Article.objects.create(headline="x", number=5, body="z")
        Article.objects.create(headline="y", number=20, body="z")
        time.sleep(1)

    def test_search_range(self):
        qs = Article.objects.annotate(score=SearchRange(path="number", gte=10, lt=30))
        self.assertEqual(qs.first().number, 20)


class SearchRegexTest(TestCase, CreateIndexMixin):
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
        Article.objects.create(headline="hello world", number=1, body="abc")
        time.sleep(1)

    def test_search_regex(self):
        qs = Article.objects.annotate(
            score=SearchRegex(path="headline", query="hello.*", allow_analyzed_field=False)
        )
        self.assertTrue(qs.first().headline.startswith("hello"))


class SearchTextTest(TestCase, CreateIndexMixin):
    def setUp(self):
        self.create_search_index(
            Article,
            "text_body_index",
            {"mappings": {"dynamic": False, "fields": {"body": {"type": "string"}}}},
        )
        Article.objects.create(headline="ignored", number=1, body="The lazy dog sleeps")
        time.sleep(1)

    def test_search_text(self):
        qs = Article.objects.annotate(score=SearchText(path="body", query="lazy"))
        self.assertIn("lazy", qs.first().body)

    def test_search_text_with_fuzzy_and_criteria(self):
        qs = Article.objects.annotate(
            score=SearchText(
                path="body", query="lazzy", fuzzy={"maxEdits": 1}, match_criteria="all"
            )
        )
        self.assertIn("lazy", qs.first().body)


class SearchWildcardTest(TestCase, CreateIndexMixin):
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
        Article.objects.create(headline="dark-knight", number=1, body="")
        time.sleep(1)

    def test_search_wildcard(self):
        qs = Article.objects.annotate(score=SearchWildcard(path="headline", query="dark-*"))
        self.assertIn("dark", qs.first().headline)


class SearchGeoShapeTest(TestCase, CreateIndexMixin):
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
        Article.objects.create(
            headline="any", number=1, body="", location={"type": "Point", "coordinates": [40, 5]}
        )
        time.sleep(1)

    def test_search_geo_shape(self):
        polygon = {
            "type": "Polygon",
            "coordinates": [[[30, 0], [50, 0], [50, 10], [30, 10], [30, 0]]],
        }
        qs = Article.objects.annotate(
            score=SearchGeoShape(path="location", relation="within", geometry=polygon)
        )
        self.assertEqual(qs.first().number, 1)


class SearchGeoWithinTest(TestCase, CreateIndexMixin):
    def setUp(self):
        self.create_search_index(
            Article,
            "geowithin_location_index",
            {"mappings": {"dynamic": False, "fields": {"location": {"type": "geo"}}}},
        )
        Article.objects.create(
            headline="geo", number=2, body="", location={"type": "Point", "coordinates": [40, 5]}
        )
        time.sleep(1)

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
        self.assertEqual(qs.first().number, 2)


class SearchMoreLikeThisTest(TestCase, CreateIndexMixin):
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
        time.sleep(1)

    def test_search_more_like_this(self):
        like_docs = [
            {"headline": self.article1.headline, "body": self.article1.body},
            {"headline": self.article2.headline, "body": self.article2.body},
        ]
        like_docs = [{"body": "NASA launches new satellite to explore the galaxy"}]
        qs = Article.objects.annotate(score=SearchMoreLikeThis(documents=like_docs)).order_by(
            "score"
        )
        self.assertQuerySetEqual(
            qs, ["space exploration", "The commodities fall"], lambda a: a.headline
        )
