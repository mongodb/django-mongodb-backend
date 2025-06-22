from django.test import TestCase

from .models import Article

from django_mongodb_backend.functions import SearchEquals


class SearchTests(TestCase):
    def test_1(self):
        Article.objects.create(headline="cross", number=1, body="body")
        aa = Article.objects.annotate(score=SearchEquals(path="headline", value="cross")).all()
        print(aa)
