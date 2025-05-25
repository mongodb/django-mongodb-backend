from datetime import date

from django.core.exceptions import FieldDoesNotExist
from django.db import connection, models
from django.test import SimpleTestCase, TestCase
from django.test.utils import CaptureQueriesContext, isolate_apps

from django_mongodb_backend.fields import EmbeddedModelArrayField
from django_mongodb_backend.models import EmbeddedModel

from .models import (
    ArtifactDetail,
    ExhibitSection,
    Movie,
    MuseumExhibit,
    RestorationRecord,
    Review,
)


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
        cls.egypt = MuseumExhibit.objects.create(
            exhibit_name="Ancient Egypt",
            sections=[
                ExhibitSection(
                    section_number=1,
                    artifacts=[
                        ArtifactDetail(
                            name="Ptolemaic Crown",
                            metadata={
                                "origin": "Egypt",
                            },
                        )
                    ],
                )
            ],
        )
        cls.wonders = MuseumExhibit.objects.create(
            exhibit_name="Wonders of the Ancient World",
            sections=[
                ExhibitSection(
                    section_number=1,
                    artifacts=[
                        ArtifactDetail(
                            name="Statue of Zeus",
                            metadata={"location": "Olympia", "height_m": 12},
                        ),
                        ArtifactDetail(
                            name="Hanging Gardens",
                        ),
                    ],
                ),
            ],
        )
        cls.new_descoveries = MuseumExhibit.objects.create(
            exhibit_name="New Discoveries",
            sections=[
                ExhibitSection(
                    section_number=2,
                    artifacts=[
                        ArtifactDetail(
                            name="Lighthouse of Alexandria",
                            metadata={"height_m": 100, "built": "3rd century BC"},
                        )
                    ],
                )
            ],
        )
        cls.lost_empires = MuseumExhibit.objects.create(
            exhibit_name="Lost Empires",
            main_section=ExhibitSection(
                section_number=3,
                artifacts=[
                    ArtifactDetail(
                        name="Bronze Statue",
                        metadata={"origin": "Pergamon"},
                        restorations=[
                            RestorationRecord(
                                date=date(1998, 4, 15),
                                restored_by="Zacarias",
                            ),
                            RestorationRecord(
                                date=date(2010, 7, 22),
                                restored_by="Vicente",
                            ),
                        ],
                        last_restoration=RestorationRecord(
                            date=date(2010, 7, 22),
                            restored_by="Monzon",
                        ),
                    )
                ],
            ),
        )

    def test_filter_with_field(self):
        self.assertCountEqual(
            Movie.objects.filter(reviews__title="Horrible"), [self.clouds, self.frozen]
        )

    def test_filter_with_embeddedfield_path(self):
        self.assertCountEqual(
            MuseumExhibit.objects.filter(sections__0__section_number=1),
            [self.egypt, self.wonders],
        )

    def test_filter_with_embeddedfield_array_path(self):
        self.assertCountEqual(
            MuseumExhibit.objects.filter(
                main_section__artifacts__restorations__0__restored_by="Zacarias"
            ),
            [self.lost_empires],
        )

    def test_filter_unsupported_lookups(self):
        # handle the unsupported lookups as key in a keytransform
        for lookup in ["contained_by", "contains", "contains", "range"]:
            kwargs = {f"main_section__artifacts__metadata__origin__{lookup}": ["Pergamon", "Egypt"]}
            with CaptureQueriesContext(connection) as captured_queries:
                self.assertCountEqual(MuseumExhibit.objects.filter(**kwargs), [])
                self.assertIn(f"'field': '{lookup}'", captured_queries[0]["sql"])

    def test_len(self):
        self.assertCountEqual(MuseumExhibit.objects.filter(sections__len=10), [])
        self.assertCountEqual(
            MuseumExhibit.objects.filter(sections__len=1),
            [self.egypt, self.wonders, self.new_descoveries],
        )
        # Nested EMF
        self.assertCountEqual(
            MuseumExhibit.objects.filter(main_section__artifacts__len=1), [self.lost_empires]
        )
        self.assertCountEqual(MuseumExhibit.objects.filter(main_section__artifacts__len=2), [])
        self.assertCountEqual(MuseumExhibit.objects.filter(main_section__artifacts__len=2), [])
        # Nested Indexed Array
        self.assertCountEqual(
            MuseumExhibit.objects.filter(sections__0__artifacts__len=2), [self.wonders]
        )
        self.assertCountEqual(MuseumExhibit.objects.filter(sections__0__artifacts__len=0), [])
        self.assertCountEqual(MuseumExhibit.objects.filter(sections__1__artifacts__len=1), [])

    def test_overlap_simplefield(self):
        self.assertSequenceEqual(
            MuseumExhibit.objects.filter(sections__section_number__overlap=[10]), []
        )
        self.assertSequenceEqual(
            MuseumExhibit.objects.filter(sections__section_number__overlap=[1]),
            [self.egypt, self.wonders],
        )
        self.assertSequenceEqual(
            MuseumExhibit.objects.filter(sections__section_number__overlap=[2]),
            [self.new_descoveries],
        )
        self.assertSequenceEqual(
            MuseumExhibit.objects.filter(sections__section_number__overlap=[3]), []
        )

    def test_missing_field(self):
        msg = "ExhibitSection has no field named 'section'"
        with self.assertRaisesMessage(FieldDoesNotExist, msg):
            self.assertSequenceEqual(
                MuseumExhibit.objects.filter(sections__section__overlap=[10]), []
            )

    def test_missing_lookup(self):
        msg = "Unsupported lookup 'return' for EmbeddedModelArrayField of type 'IntegerField'"
        with self.assertRaisesMessage(FieldDoesNotExist, msg):
            self.assertSequenceEqual(
                MuseumExhibit.objects.filter(sections__section_number__return=3), []
            )

    def test_missing_lookup_suggestions(self):
        msg = (
            "Unsupported lookup 'ltee' for EmbeddedModelArrayField of 'IntegerField', "
            "perhaps you meant lte or lt?"
        )
        with self.assertRaisesMessage(FieldDoesNotExist, msg):
            self.assertSequenceEqual(
                MuseumExhibit.objects.filter(sections__section_number__ltee=3), []
            )


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
