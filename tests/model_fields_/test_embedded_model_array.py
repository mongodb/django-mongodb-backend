from django.core.exceptions import FieldError
from django.db import models
from django.test import SimpleTestCase, TestCase
from django.test.utils import isolate_apps

from django_mongodb_backend.fields import EmbeddedModelArrayField
from django_mongodb_backend.models import EmbeddedModel

from .models import Movie, Review


class MethodTests(SimpleTestCase):
    def test_deconstruct(self):
        field = EmbeddedModelArrayField("Data", null=True)
        name, path, args, kwargs = field.deconstruct()
        self.assertEqual(path, "django_mongodb_backend.fields.EmbeddedModelArrayField")
        self.assertEqual(args, [])
        self.assertEqual(kwargs, {"embedded_model": "Data", "null": True})

    def test_size_not_supported(self):
        msg = "EmbeddedModelArrayField does not support size."
        with self.assertRaisesMessage(ValueError, msg):
            EmbeddedModelArrayField("Data", size=1)

    def test_get_db_prep_save_invalid(self):
        msg = "Expected list of <class 'model_fields_.models.Review'> instances, not <class 'int'>."
        with self.assertRaisesMessage(TypeError, msg):
            Movie(reviews=42).save()

    def test_get_db_prep_save_invalid_list(self):
        msg = "Expected instance of type <class 'model_fields_.models.Review'>, not <class 'int'>."
        with self.assertRaisesMessage(TypeError, msg):
            Movie(reviews=[42]).save()


class ModelTests(TestCase):
    def test_save_load(self):
        reviews = [
            Review(title="The best", rating=10),
            Review(title="Mediocre", rating=5),
            Review(title="Horrible", rating=1),
        ]
        Movie.objects.create(title="Lion King", reviews=reviews)
        movie = Movie.objects.get(title="Lion King")
        self.assertEqual(movie.reviews[0].title, "The best")
        self.assertEqual(movie.reviews[0].rating, 10)
        self.assertEqual(movie.reviews[1].title, "Mediocre")
        self.assertEqual(movie.reviews[1].rating, 5)
        self.assertEqual(movie.reviews[2].title, "Horrible")
        self.assertEqual(movie.reviews[2].rating, 1)
        self.assertEqual(len(movie.reviews), 3)

    def test_save_load_null(self):
        movie = Movie.objects.create(title="Lion King")
        movie = Movie.objects.get(title="Lion King")
        self.assertIsNone(movie.reviews)


class QueryingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        reviews = [
            Review(title="The best", rating=10),
            Review(title="Mediocre", rating=5),
            Review(title="Horrible", rating=1),
        ]
        cls.clouds = Movie.objects.create(title="Clouds", reviews=reviews)
        reviews = [
            Review(title="Super", rating=9),
            Review(title="Meh", rating=5),
            Review(title="Horrible", rating=2),
        ]
        cls.frozen = Movie.objects.create(title="Frozen", reviews=reviews)
        reviews = [
            Review(title="Excellent", rating=9),
            Review(title="Wow", rating=8),
            Review(title="Classic", rating=7),
        ]
        cls.bears = Movie.objects.create(title="Bears", reviews=reviews)

    def test_filter_with_field(self):
        msg = (
            "Unsupported lookup 'title' for EmbeddedModelArrayField or join "
            "on the field not permitted."
        )
        with self.assertRaisesMessage(FieldError, msg):
            Movie.objects.filter(reviews__title="Horrible")


@isolate_apps("model_fields_")
class CheckTests(SimpleTestCase):
    def test_no_relational_fields(self):
        class Target(EmbeddedModel):
            key = models.ForeignKey("MyModel", models.CASCADE)

        class MyModel(models.Model):
            field = EmbeddedModelArrayField(Target)

        errors = MyModel().check()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].id, "django_mongodb_backend.array.E001")
        msg = errors[0].msg
        self.assertEqual(
            msg,
            "Base field for array has errors:\n    "
            "Embedded models cannot have relational fields (Target.key is a ForeignKey). "
            "(django_mongodb_backend.embedded_model.E001)",
        )

    def test_embedded_model_subclass(self):
        class Target(models.Model):
            pass

        class MyModel(models.Model):
            field = EmbeddedModelArrayField(Target)

        errors = MyModel().check()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].id, "django_mongodb_backend.array.E001")
        msg = errors[0].msg
        self.assertEqual(
            msg,
            "Base field for array has errors:\n    "
            "Embedded models must be a subclass of "
            "django_mongodb_backend.models.EmbeddedModel. "
            "(django_mongodb_backend.embedded_model.E002)",
        )
