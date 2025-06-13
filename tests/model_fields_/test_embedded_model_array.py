import unittest
from datetime import date

from django.core.exceptions import FieldDoesNotExist
from django.db import connection, models
from django.db.models.expressions import Value
from django.test import SimpleTestCase, TestCase
from django.test.utils import CaptureQueriesContext, isolate_apps

from django_mongodb_backend.fields import ArrayField, EmbeddedModelArrayField
from django_mongodb_backend.models import EmbeddedModel

from .models import Artifact, Audit, Exhibit, Movie, Restoration, Review, Section, Tour


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
        cls.egypt = Exhibit.objects.create(
            exhibit_name="Ancient Egypt",
            sections=[
                Section(
                    section_number=1,
                    artifacts=[
                        Artifact(
                            name="Ptolemaic Crown",
                            metadata={
                                "origin": "Egypt",
                            },
                        )
                    ],
                )
            ],
        )
        cls.wonders = Exhibit.objects.create(
            exhibit_name="Wonders of the Ancient World",
            sections=[
                Section(
                    section_number=1,
                    artifacts=[
                        Artifact(
                            name="Statue of Zeus",
                            metadata={"location": "Olympia", "height_m": 12},
                        ),
                        Artifact(
                            name="Hanging Gardens",
                        ),
                    ],
                ),
                Section(
                    section_number=2,
                    artifacts=[
                        Artifact(
                            name="Lighthouse of Alexandria",
                            metadata={"height_m": 100, "built": "3rd century BC"},
                        )
                    ],
                ),
            ],
        )
        cls.new_descoveries = Exhibit.objects.create(
            exhibit_name="New Discoveries",
            sections=[
                Section(
                    section_number=2,
                    artifacts=[
                        Artifact(
                            name="Lighthouse of Alexandria",
                            metadata={"height_m": 100, "built": "3rd century BC"},
                        )
                    ],
                )
            ],
            main_section=Section(section_number=2),
        )
        cls.lost_empires = Exhibit.objects.create(
            exhibit_name="Lost Empires",
            main_section=Section(
                section_number=3,
                artifacts=[
                    Artifact(
                        name="Bronze Statue",
                        metadata={"origin": "Pergamon"},
                        restorations=[
                            Restoration(
                                date=date(1998, 4, 15),
                                restored_by="Zacarias",
                            ),
                            Restoration(
                                date=date(2010, 7, 22),
                                restored_by="Vicente",
                            ),
                        ],
                        last_restoration=Restoration(
                            date=date(2010, 7, 22),
                            restored_by="Monzon",
                        ),
                    )
                ],
            ),
        )
        cls.egypt_tour = Tour.objects.create(guide="Amira", exhibit=cls.egypt)
        cls.wonders_tour = Tour.objects.create(guide="Carlos", exhibit=cls.wonders)
        cls.lost_tour = Tour.objects.create(guide="Yelena", exhibit=cls.lost_empires)
        cls.audit_1 = Audit.objects.create(section_number=1, reviewed=True)
        cls.audit_2 = Audit.objects.create(section_number=2, reviewed=True)
        cls.audit_3 = Audit.objects.create(section_number=5, reviewed=False)

    def test_exact(self):
        self.assertCountEqual(
            Exhibit.objects.filter(sections__section_number=1), [self.egypt, self.wonders]
        )

    def test_array_index(self):
        self.assertCountEqual(
            Exhibit.objects.filter(sections__0__section_number=1),
            [self.egypt, self.wonders],
        )

    def test_nested_array_index(self):
        self.assertCountEqual(
            Exhibit.objects.filter(
                main_section__artifacts__restorations__0__restored_by="Zacarias"
            ),
            [self.lost_empires],
        )

    def test_array_slice(self):
        self.assertSequenceEqual(
            Exhibit.objects.filter(sections__0_1__section_number=2), [self.new_descoveries]
        )

    def test_filter_unsupported_lookups_in_json(self):
        """Unsupported lookups can be used as keys in a JSONField."""
        for lookup in ["contains", "range"]:
            kwargs = {f"main_section__artifacts__metadata__origin__{lookup}": ["Pergamon", "Egypt"]}
            with CaptureQueriesContext(connection) as captured_queries:
                self.assertCountEqual(Exhibit.objects.filter(**kwargs), [])
                self.assertIn(f"'field': '{lookup}'", captured_queries[0]["sql"])

    def test_len(self):
        self.assertCountEqual(Exhibit.objects.filter(sections__len=10), [])
        self.assertCountEqual(
            Exhibit.objects.filter(sections__len=1),
            [self.egypt, self.new_descoveries],
        )
        # Nested EMF
        self.assertCountEqual(
            Exhibit.objects.filter(main_section__artifacts__len=1), [self.lost_empires]
        )
        self.assertCountEqual(Exhibit.objects.filter(main_section__artifacts__len=2), [])
        # Nested Indexed Array
        self.assertCountEqual(Exhibit.objects.filter(sections__0__artifacts__len=2), [self.wonders])
        self.assertCountEqual(Exhibit.objects.filter(sections__0__artifacts__len=0), [])
        self.assertCountEqual(Exhibit.objects.filter(sections__1__artifacts__len=1), [self.wonders])

    def test_in(self):
        self.assertCountEqual(Exhibit.objects.filter(sections__section_number__in=[10]), [])
        self.assertCountEqual(
            Exhibit.objects.filter(sections__section_number__in=[1]),
            [self.egypt, self.wonders],
        )
        self.assertCountEqual(
            Exhibit.objects.filter(sections__section_number__in=[2]),
            [self.new_descoveries, self.wonders],
        )
        self.assertCountEqual(Exhibit.objects.filter(sections__section_number__in=[3]), [])

    def test_iexact(self):
        self.assertCountEqual(
            Exhibit.objects.filter(sections__artifacts__0__name__iexact="lightHOuse of aLexandriA"),
            [self.new_descoveries, self.wonders],
        )

    def test_gt(self):
        self.assertCountEqual(
            Exhibit.objects.filter(sections__section_number__gt=1),
            [self.new_descoveries, self.wonders],
        )

    def test_gte(self):
        self.assertCountEqual(
            Exhibit.objects.filter(sections__section_number__gte=1),
            [self.egypt, self.new_descoveries, self.wonders],
        )

    def test_lt(self):
        self.assertCountEqual(
            Exhibit.objects.filter(sections__section_number__lt=2), [self.egypt, self.wonders]
        )

    def test_lte(self):
        self.assertCountEqual(
            Exhibit.objects.filter(sections__section_number__lte=2),
            [self.egypt, self.wonders, self.new_descoveries],
        )

    def test_querying_array_not_allowed(self):
        msg = (
            "Lookups aren't supported on EmbeddedModelArrayField. "
            "Try querying one of its embedded fields instead."
        )
        with self.assertRaisesMessage(ValueError, msg):
            Exhibit.objects.filter(sections=10).first()

        with self.assertRaisesMessage(ValueError, msg):
            Exhibit.objects.filter(sections__0_1=10).first()

    def test_invalid_field(self):
        msg = "Section has no field named 'section'"
        with self.assertRaisesMessage(FieldDoesNotExist, msg):
            Exhibit.objects.filter(sections__section__in=[10]).first()

    def test_invalid_lookup(self):
        msg = "Unsupported lookup 'return' for EmbeddedModelArrayField of 'IntegerField'"
        with self.assertRaisesMessage(FieldDoesNotExist, msg):
            Exhibit.objects.filter(sections__section_number__return=3)

    def test_invalid_operation(self):
        msg = "Unsupported lookup 'rage' for EmbeddedModelArrayField of 'IntegerField'"
        with self.assertRaisesMessage(FieldDoesNotExist, msg):
            Exhibit.objects.filter(sections__section_number__rage=[10])

    def test_missing_lookup_suggestions(self):
        msg = (
            "Unsupported lookup 'ltee' for EmbeddedModelArrayField of 'IntegerField', "
            "perhaps you meant lte or lt?"
        )
        with self.assertRaisesMessage(FieldDoesNotExist, msg):
            Exhibit.objects.filter(sections__section_number__ltee=3)

    def test_nested_lookup(self):
        msg = "Cannot perform multiple levels of array traversal in a query."
        with self.assertRaisesMessage(ValueError, msg):
            Exhibit.objects.filter(sections__artifacts__name="")

    def test_foreign_field_exact(self):
        """Querying from a foreign key to an EmbeddedModelArrayField."""
        qs = Tour.objects.filter(exhibit__sections__section_number=1)
        self.assertCountEqual(qs, [self.egypt_tour, self.wonders_tour])

    def test_foreign_field_with_slice(self):
        qs = Tour.objects.filter(exhibit__sections__0_2__section_number__in=[1, 2])
        self.assertCountEqual(qs, [self.wonders_tour, self.egypt_tour])

    def test_subquery_numeric_lookups(self):
        subq = Audit.objects.filter(
            section_number__in=models.OuterRef("sections__section_number")
        ).values("section_number")[:1]
        lookups_expected_value = [
            ("exact", [self.egypt, self.new_descoveries, self.wonders]),
            ("lt", []),
            ("lte", [self.egypt, self.new_descoveries, self.wonders]),
            ("gt", [self.wonders]),
            ("gte", [self.egypt, self.new_descoveries, self.wonders]),
        ]
        for lookup, expected_value in lookups_expected_value:
            with self.subTest(key=lookup):
                kwargs = {f"sections__section_number__{lookup}": subq}
                self.assertCountEqual(Exhibit.objects.filter(**kwargs), expected_value)

    def test_in_subquery(self):
        subquery = Audit.objects.filter(reviewed=True).values_list("section_number", flat=True)
        result = Exhibit.objects.filter(sections__section_number__in=subquery)
        self.assertCountEqual(result, [self.wonders, self.new_descoveries, self.egypt])

    def test_array_as_rhs(self):
        result = Exhibit.objects.filter(
            main_section__section_number__in=models.F("sections__section_number")
        )
        self.assertCountEqual(result, [self.new_descoveries])

    def test_array_annotation_lookup(self):
        result = Exhibit.objects.annotate(
            section_numbers=models.F("main_section__section_number")
        ).filter(section_numbers__in=models.F("sections__section_number"))
        self.assertCountEqual(result, [self.new_descoveries])

    def test_array_as_rhs_behavior_for_arrayfield_lookups(self):
        lookup_expected_value = [
            ("exact", [self.wonders]),
            ("lt", [self.new_descoveries]),
            ("lte", [self.wonders, self.new_descoveries]),
            ("gt", [self.egypt, self.lost_empires]),
            ("gte", [self.egypt, self.wonders, self.lost_empires]),
            ("overlap", [self.egypt, self.wonders, self.new_descoveries]),
            ("contained_by", [self.wonders]),
            ("contains", [self.egypt, self.wonders, self.new_descoveries, self.lost_empires]),
        ]
        for lookup, expected in lookup_expected_value:
            with self.subTest(key=lookup):
                kwargs = {f"section_numbers__{lookup}": models.F("sections__section_number")}
                result = Exhibit.objects.annotate(
                    section_numbers=Value(
                        [1, 2], output_field=ArrayField(base_field=models.IntegerField())
                    )
                ).filter(**kwargs)
                self.assertCountEqual(result, expected)

    @unittest.expectedFailure
    def test_array_annotation_index(self):
        # This test would be useful to have, but it cannot be implemented
        # due to the current annotation handling.
        # Supporting slicing or indexing over an annotated
        # Embedded Array Field would require a refactor.
        result = Exhibit.objects.annotate(
            section_numbers=models.F("sections__section_number")
        ).filter(section_numbers__0=1)
        self.assertCountEqual(result, [self.new_descoveries, self.egypt])

    def test_array_annotation(self):
        results = Exhibit.objects.annotate(section_numbers=models.F("sections__section_number"))
        sections_numbers = [e.section_numbers for e in results]
        self.assertCountEqual(sections_numbers, [[1], [1, 2], [2], []])


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
