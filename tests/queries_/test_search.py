from django.test import TestCase

from django_mongodb_backend.functions import SearchEquals

from .models import Article


class SearchTests(TestCase):
    def test_1(self):
        Article.objects.create(headline="cross", number=1, body="body")
        aa = Article.objects.annotate(score=SearchEquals(path="headline", value="cross")).all()
        self.assertEqual(aa.score == 1)
        # print(aa)
