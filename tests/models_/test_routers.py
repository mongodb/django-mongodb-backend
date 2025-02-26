from django.test import SimpleTestCase

from django_mongodb_backend.routers import MongoRouter


class TestRouter(SimpleTestCase):
    def setUp(self):
        self.router = MongoRouter()

    def test_no_model(self):
        self.assertIsNone(self.router.allow_migrate("db", "models_"))

    def test_regular_model(self):
        self.assertIsNone(self.router.allow_migrate("db", "models_", "plainmodel"))

    def test_nonexistent_model(self):
        self.assertIsNone(self.router.allow_migrate("db", "models_", "nonexistentmodel"))

    def test_embedded_model(self):
        self.assertIs(self.router.allow_migrate("db", "models_", "embed"), False)
