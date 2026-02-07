from bson import ObjectId
from django.test import SimpleTestCase
from django.test.utils import override_settings
from django.urls import Resolver404, resolve, reverse


@override_settings(ROOT_URLCONF="urlpatterns_.urls")
class ObjectIdConverterTests(SimpleTestCase):
    def test_resolve(self):
        match = resolve("/articles/69868bc49b827bee857500c2/")
        self.assertEqual(match.url_name, "article-detail")
        self.assertEqual(match.args, ())
        self.assertEqual(match.kwargs, {"pk": ObjectId("69868bc49b827bee857500c2")})

    def test_reverse(self):
        url = reverse("article-detail", kwargs={"pk": ObjectId("69868bc49b827bee857500c2")})
        self.assertEqual(url, "/articles/69868bc49b827bee857500c2/")

    def test_invalid_character(self):
        # Correct length, but "z" not a valid character for ObjectId.
        with self.assertRaises(Resolver404):
            resolve("/articles/69868bc49b827bee857500cz/")

    def test_too_few_characters(self):
        # ObjectId must be 24 characters, not 23.
        with self.assertRaises(Resolver404):
            resolve("/articles/69868bc49b827bee857500c/")

    def test_too_many_characters(self):
        # ObjectId must be 24 characters, not 25.
        with self.assertRaises(Resolver404):
            resolve("/articles/69868bc49b827bee857500c21/")
