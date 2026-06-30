from unittest import mock

from django.db import models
from django.db.migrations.questioner import MigrationQuestioner
from django.db.migrations.state import ModelState

from django_mongodb_backend.fields import EmbeddedModelField, ObjectIdAutoField

from .base import BaseAutodetectorTests


class EmbeddedModelFieldAutodetectorTests(BaseAutodetectorTests):
    """Test the autodetector with EmbeddedModelField."""

    def test_add_embedded_field(self):
        """Detection of new embedded fields (Author.age)."""
        changes = self.get_changes(
            [
                ModelState(
                    "testapp",
                    "Book",
                    [
                        ("id", ObjectIdAutoField(primary_key=True)),
                        ("name", models.CharField(max_length=200)),
                        ("author", EmbeddedModelField("testapp.author")),
                    ],
                ),
                ModelState(
                    "testapp",
                    "Author",
                    [
                        ("id", ObjectIdAutoField(primary_key=True)),
                        ("name", models.CharField(max_length=10)),
                    ],
                    {"managed": False},
                ),
            ],
            [
                ModelState(
                    "testapp",
                    "Book",
                    [
                        ("id", ObjectIdAutoField(primary_key=True)),
                        ("name", models.CharField(max_length=200)),
                        ("author", EmbeddedModelField("testapp.author")),
                    ],
                ),
                ModelState(
                    "testapp",
                    "Author",
                    [
                        ("id", ObjectIdAutoField(primary_key=True)),
                        ("name", models.CharField(max_length=10)),
                        ("age", models.IntegerField()),
                    ],
                    {"managed": False},
                ),
            ],
        )
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(changes, "testapp", 0, ["AddField", "AddEmbeddedField"])
        self.assertOperationAttributes(
            changes,
            "testapp",
            0,
            1,
            model_name="book",
            name="author.age",
        )

    def test_add_embedded_field_db_column(self):
        """
        AddEmbeddedField's name uses each field's db_column in embedded paths.
        """
        changes = self.get_changes(
            [
                ModelState(
                    "testapp",
                    "Book",
                    [
                        ("id", ObjectIdAutoField(primary_key=True)),
                        ("name", models.CharField(max_length=200)),
                        ("author", EmbeddedModelField("testapp.author", db_column="the_author")),
                    ],
                ),
                ModelState(
                    "testapp",
                    "Author",
                    [
                        ("id", ObjectIdAutoField(primary_key=True)),
                        ("name", models.CharField(max_length=10)),
                    ],
                    {"managed": False},
                ),
            ],
            [
                ModelState(
                    "testapp",
                    "Book",
                    [
                        ("id", ObjectIdAutoField(primary_key=True)),
                        ("name", models.CharField(max_length=200)),
                        ("author", EmbeddedModelField("testapp.author", db_column="the_author")),
                    ],
                ),
                ModelState(
                    "testapp",
                    "Author",
                    [
                        ("id", ObjectIdAutoField(primary_key=True)),
                        ("name", models.CharField(max_length=10)),
                        ("age", models.IntegerField(db_column="the_age")),
                    ],
                    {"managed": False},
                ),
            ],
        )
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(changes, "testapp", 0, ["AddField", "AddEmbeddedField"])
        self.assertOperationAttributes(
            changes,
            "testapp",
            0,
            1,
            model_name="book",
            name="the_author.the_age",
        )

    @mock.patch(
        "django.db.migrations.questioner.MigrationQuestioner.ask_not_null_addition",
        side_effect=AssertionError("Should not have prompted for not null addition"),
    )
    def test_add_date_fields_with_auto_now_not_asking_for_default(self, mocked_ask_method):
        changes = self.get_changes(
            [
                ModelState(
                    "testapp",
                    "Book",
                    [
                        ("id", ObjectIdAutoField(primary_key=True)),
                        ("name", models.CharField(max_length=200)),
                        ("author", EmbeddedModelField("testapp.author")),
                    ],
                ),
                ModelState(
                    "testapp",
                    "Author",
                    [
                        ("id", ObjectIdAutoField(primary_key=True)),
                        ("name", models.CharField(max_length=10)),
                    ],
                    {"managed": False},
                ),
            ],
            [
                ModelState(
                    "testapp",
                    "Book",
                    [
                        ("id", ObjectIdAutoField(primary_key=True)),
                        ("name", models.CharField(max_length=200)),
                        ("author", EmbeddedModelField("testapp.author")),
                    ],
                ),
                ModelState(
                    "testapp",
                    "Author",
                    [
                        ("id", ObjectIdAutoField(primary_key=True)),
                        ("name", models.CharField(max_length=10)),
                        ("date", models.DateField(auto_now=True)),
                        ("datetime", models.DateTimeField(auto_now=True)),
                        ("time", models.TimeField(auto_now=True)),
                    ],
                    {"managed": False},
                ),
            ],
        )
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(
            changes, "testapp", 0, ["AddField"] * 3 + ["AddEmbeddedField"] * 3
        )
        self.assertOperationAttributes(changes, "testapp", 0, 0, name="date", preserve_default=True)
        self.assertOperationFieldAttributes(changes, "testapp", 0, 0, auto_now=True)
        self.assertOperationFieldAttributes(changes, "testapp", 0, 1, auto_now=True)
        self.assertOperationFieldAttributes(changes, "testapp", 0, 2, auto_now=True)

    @mock.patch(
        "django.db.migrations.questioner.MigrationQuestioner.ask_not_null_addition",
        side_effect=AssertionError("Should not have prompted for not null addition"),
    )
    def test_add_date_fields_with_auto_now_add_not_asking_for_null_addition(
        self, mocked_ask_method
    ):
        changes = self.get_changes(
            [
                ModelState(
                    "testapp",
                    "Book",
                    [
                        ("id", ObjectIdAutoField(primary_key=True)),
                        ("name", models.CharField(max_length=200)),
                        ("author", EmbeddedModelField("testapp.author")),
                    ],
                ),
                ModelState(
                    "testapp",
                    "Author",
                    [
                        ("id", ObjectIdAutoField(primary_key=True)),
                        ("name", models.CharField(max_length=10)),
                    ],
                    {"managed": False},
                ),
            ],
            [
                ModelState(
                    "testapp",
                    "Book",
                    [
                        ("id", ObjectIdAutoField(primary_key=True)),
                        ("name", models.CharField(max_length=200)),
                        ("author", EmbeddedModelField("testapp.author")),
                    ],
                ),
                ModelState(
                    "testapp",
                    "Author",
                    [
                        ("id", ObjectIdAutoField(primary_key=True)),
                        ("name", models.CharField(max_length=10)),
                        ("date", models.DateField(auto_now_add=True)),
                        ("datetime", models.DateTimeField(auto_now_add=True)),
                        ("time", models.TimeField(auto_now_add=True)),
                    ],
                    {"managed": False},
                ),
            ],
        )
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(
            changes, "testapp", 0, ["AddField"] * 3 + ["AddEmbeddedField"] * 3
        )
        self.assertOperationAttributes(
            changes, "testapp", 0, 0, name="date", preserve_default=False
        )
        self.assertOperationAttributes(
            changes, "testapp", 0, 1, name="datetime", preserve_default=False
        )
        self.assertOperationAttributes(
            changes, "testapp", 0, 2, name="time", preserve_default=False
        )
        self.assertOperationAttributes(
            changes, "testapp", 0, 3, name="author.date", preserve_default=False
        )
        self.assertOperationAttributes(
            changes, "testapp", 0, 4, name="author.datetime", preserve_default=False
        )
        self.assertOperationAttributes(
            changes, "testapp", 0, 5, name="author.time", preserve_default=False
        )
        self.assertOperationFieldAttributes(changes, "testapp", 0, 0, auto_now_add=True)
        self.assertOperationFieldAttributes(changes, "testapp", 0, 1, auto_now_add=True)
        self.assertOperationFieldAttributes(changes, "testapp", 0, 2, auto_now_add=True)
        self.assertOperationFieldAttributes(changes, "testapp", 0, 3, auto_now_add=True)
        self.assertOperationFieldAttributes(changes, "testapp", 0, 4, auto_now_add=True)
        self.assertOperationFieldAttributes(changes, "testapp", 0, 5, auto_now_add=True)

    @mock.patch("django.db.migrations.questioner.MigrationQuestioner.ask_auto_now_add_addition")
    def test_add_date_fields_with_auto_now_add_asking_for_default(self, mocked_ask_method):
        changes = self.get_changes(
            [
                ModelState(
                    "testapp",
                    "Book",
                    [
                        ("id", ObjectIdAutoField(primary_key=True)),
                        ("name", models.CharField(max_length=200)),
                        ("author", EmbeddedModelField("testapp.author")),
                    ],
                ),
                ModelState(
                    "testapp",
                    "Author",
                    [
                        ("id", ObjectIdAutoField(primary_key=True)),
                        ("name", models.CharField(max_length=10)),
                    ],
                    {"managed": False},
                ),
            ],
            [
                ModelState(
                    "testapp",
                    "Book",
                    [
                        ("id", ObjectIdAutoField(primary_key=True)),
                        ("name", models.CharField(max_length=200)),
                        ("author", EmbeddedModelField("testapp.author")),
                    ],
                ),
                ModelState(
                    "testapp",
                    "Author",
                    [
                        ("id", ObjectIdAutoField(primary_key=True)),
                        ("name", models.CharField(max_length=10)),
                        ("date", models.DateField(auto_now_add=True)),
                        ("datetime", models.DateTimeField(auto_now_add=True)),
                        ("time", models.TimeField(auto_now_add=True)),
                    ],
                    {"managed": False},
                ),
            ],
        )
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(
            changes, "testapp", 0, ["AddField"] * 3 + ["AddEmbeddedField"] * 3
        )
        self.assertOperationAttributes(
            changes, "testapp", 0, 0, name="date", preserve_default=False
        )
        self.assertOperationAttributes(
            changes, "testapp", 0, 1, name="datetime", preserve_default=False
        )
        self.assertOperationAttributes(
            changes, "testapp", 0, 2, name="time", preserve_default=False
        )
        self.assertOperationFieldAttributes(changes, "testapp", 0, 0, auto_now_add=True)
        self.assertOperationFieldAttributes(changes, "testapp", 0, 1, auto_now_add=True)
        self.assertOperationFieldAttributes(changes, "testapp", 0, 2, auto_now_add=True)
        self.assertEqual(mocked_ask_method.call_count, 3)

    def test_add_nested_embedded_field(self):
        """Detection of new nested embedded fields (Book.author.bio.title)."""
        changes = self.get_changes(
            [
                ModelState(
                    "testapp",
                    "Book",
                    [
                        ("id", ObjectIdAutoField(primary_key=True)),
                        ("name", models.CharField(max_length=200)),
                        ("author", EmbeddedModelField("testapp.author")),
                    ],
                ),
                ModelState(
                    "testapp",
                    "Author",
                    [
                        ("id", ObjectIdAutoField(primary_key=True)),
                        ("name", models.CharField(max_length=10)),
                        ("bio", EmbeddedModelField("testapp.bio")),
                    ],
                    {"managed": False},
                ),
                ModelState(
                    "testapp",
                    "Bio",
                    [
                        ("id", ObjectIdAutoField(primary_key=True)),
                    ],
                    {"managed": False},
                ),
            ],
            [
                ModelState(
                    "testapp",
                    "Book",
                    [
                        ("id", ObjectIdAutoField(primary_key=True)),
                        ("name", models.CharField(max_length=200)),
                        ("author", EmbeddedModelField("testapp.author")),
                    ],
                ),
                ModelState(
                    "testapp",
                    "Author",
                    [
                        ("id", ObjectIdAutoField(primary_key=True)),
                        ("name", models.CharField(max_length=10)),
                        ("bio", EmbeddedModelField("testapp.bio")),
                    ],
                    {"managed": False},
                ),
                ModelState(
                    "testapp",
                    "Bio",
                    [
                        ("id", ObjectIdAutoField(primary_key=True)),
                        ("title", models.CharField(max_length=10)),  # Added
                    ],
                    {"managed": False},
                ),
            ],
        )
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(changes, "testapp", 0, ["AddField", "AddEmbeddedField"])
        self.assertOperationAttributes(changes, "testapp", 0, 0, model_name="bio", name="title")
        self.assertOperationAttributes(
            changes, "testapp", 0, 1, model_name="book", name="author.bio.title"
        )

    def test_add_embedded_model_field(self):
        """Detection of new embedded model fields (Book.author)."""
        changes = self.get_changes(
            [
                ModelState(
                    "testapp",
                    "Book",
                    [
                        ("id", ObjectIdAutoField(primary_key=True)),
                        ("name", models.CharField(max_length=200)),
                    ],
                ),
                ModelState(
                    "testapp",
                    "Author",
                    [
                        ("id", ObjectIdAutoField(primary_key=True)),
                        ("name", models.CharField(max_length=10)),
                    ],
                    {"managed": False},
                ),
            ],
            [
                ModelState(
                    "testapp",
                    "Book",
                    [
                        ("id", ObjectIdAutoField(primary_key=True)),
                        ("name", models.CharField(max_length=200)),
                        ("author", EmbeddedModelField("testapp.author")),  # Added
                    ],
                ),
                ModelState(
                    "testapp",
                    "Author",
                    [
                        ("id", ObjectIdAutoField(primary_key=True)),
                        ("name", models.CharField(max_length=10)),
                    ],
                    {"managed": False},
                ),
            ],
        )
        self.assertNumberMigrations(changes, "testapp", 1)
        # Generates only AddField for the new model and not an AddEmbeddedField
        # for each subfield.
        self.assertOperationTypes(changes, "testapp", 0, ["AddField"])
        self.assertOperationAttributes(changes, "testapp", 0, 0, model_name="book", name="author")

    def test_add_nested_embedded_model_field(self):
        """Detection of new embedded model fields (Book.author)."""
        changes = self.get_changes(
            [
                ModelState(
                    "testapp",
                    "Book",
                    [
                        ("id", ObjectIdAutoField(primary_key=True)),
                        ("name", models.CharField(max_length=200)),
                        ("author", EmbeddedModelField("testapp.author")),
                    ],
                ),
                ModelState(
                    "testapp",
                    "Author",
                    [
                        ("id", ObjectIdAutoField(primary_key=True)),
                        ("name", models.CharField(max_length=10)),
                    ],
                    {"managed": False},
                ),
                ModelState(
                    "testapp",
                    "Bio",
                    [
                        ("id", ObjectIdAutoField(primary_key=True)),
                        ("title", models.CharField(max_length=10)),
                    ],
                    {"managed": False},
                ),
            ],
            [
                ModelState(
                    "testapp",
                    "Book",
                    [
                        ("id", ObjectIdAutoField(primary_key=True)),
                        ("name", models.CharField(max_length=200)),
                        ("author", EmbeddedModelField("testapp.author")),
                    ],
                ),
                ModelState(
                    "testapp",
                    "Author",
                    [
                        ("id", ObjectIdAutoField(primary_key=True)),
                        ("name", models.CharField(max_length=10)),
                        ("bio", EmbeddedModelField("testapp.bio")),  # Added
                    ],
                    {"managed": False},
                ),
                ModelState(
                    "testapp",
                    "Bio",
                    [
                        ("id", ObjectIdAutoField(primary_key=True)),
                        ("title", models.CharField(max_length=10)),
                    ],
                    {"managed": False},
                ),
            ],
        )
        self.assertNumberMigrations(changes, "testapp", 1)
        # Generates only AddEmbeddedField for the author.bio and not an
        # AddEmbeddedField for each field of Bio.
        self.assertOperationTypes(changes, "testapp", 0, ["AddField", "AddEmbeddedField"])
        self.assertOperationAttributes(changes, "testapp", 0, 0, model_name="author", name="bio")
        self.assertOperationAttributes(
            changes, "testapp", 0, 1, model_name="book", name="author.bio"
        )

    def test_remove_embedded_field(self):
        """Tests autodetection of removed fields."""
        changes = self.get_changes(
            [
                ModelState(
                    "testapp",
                    "Book",
                    [
                        ("id", ObjectIdAutoField(primary_key=True)),
                        ("name", models.CharField(max_length=200)),
                        ("author", EmbeddedModelField("testapp.author")),
                    ],
                ),
                ModelState(
                    "testapp",
                    "Author",
                    [
                        ("id", ObjectIdAutoField(primary_key=True)),
                        ("name", models.CharField(max_length=10)),
                    ],
                    {"managed": False},
                ),
            ],
            [
                ModelState(
                    "testapp",
                    "Book",
                    [
                        ("id", ObjectIdAutoField(primary_key=True)),
                        ("name", models.CharField(max_length=200)),
                        ("author", EmbeddedModelField("testapp.author")),
                    ],
                ),
                ModelState(
                    "testapp",
                    "Author",
                    [
                        ("id", ObjectIdAutoField(primary_key=True)),
                        # Removed name
                    ],
                    {"managed": False},
                ),
            ],
        )
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(changes, "testapp", 0, ["RemoveField", "RemoveEmbeddedField"])
        self.assertOperationAttributes(changes, "testapp", 0, 0, name="name")
        self.assertOperationAttributes(changes, "testapp", 0, 1, name="author.name")

    def test_remove_nested_embedded_field(self):
        """
        Detection of removed nested embedded fields (Book.author.bio.title).
        """
        changes = self.get_changes(
            [
                ModelState(
                    "testapp",
                    "Book",
                    [
                        ("id", ObjectIdAutoField(primary_key=True)),
                        ("name", models.CharField(max_length=200)),
                        ("author", EmbeddedModelField("testapp.author")),
                    ],
                ),
                ModelState(
                    "testapp",
                    "Author",
                    [
                        ("id", ObjectIdAutoField(primary_key=True)),
                        ("name", models.CharField(max_length=10)),
                        ("bio", EmbeddedModelField("testapp.bio")),
                    ],
                    {"managed": False},
                ),
                ModelState(
                    "testapp",
                    "Bio",
                    [
                        ("id", ObjectIdAutoField(primary_key=True)),
                        ("title", models.CharField(max_length=10)),
                    ],
                    {"managed": False},
                ),
            ],
            [
                ModelState(
                    "testapp",
                    "Book",
                    [
                        ("id", ObjectIdAutoField(primary_key=True)),
                        ("name", models.CharField(max_length=200)),
                        ("author", EmbeddedModelField("testapp.author")),
                    ],
                ),
                ModelState(
                    "testapp",
                    "Author",
                    [
                        ("id", ObjectIdAutoField(primary_key=True)),
                        ("name", models.CharField(max_length=10)),
                        ("bio", EmbeddedModelField("testapp.bio")),
                    ],
                    {"managed": False},
                ),
                ModelState(
                    "testapp",
                    "Bio",
                    [
                        ("id", ObjectIdAutoField(primary_key=True)),
                        # Removed title
                    ],
                    {"managed": False},
                ),
            ],
        )
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(changes, "testapp", 0, ["RemoveField", "RemoveEmbeddedField"])
        self.assertOperationAttributes(changes, "testapp", 0, 0, model_name="bio", name="title")
        self.assertOperationAttributes(
            changes, "testapp", 0, 1, model_name="book", name="author.bio.title"
        )

    def test_alter_embedded_field(self):
        """Detection of db_column change on an embedded field."""
        changes = self.get_changes(
            [
                ModelState(
                    "testapp",
                    "Book",
                    [
                        ("id", ObjectIdAutoField(primary_key=True)),
                        ("name", models.CharField(max_length=200)),
                        ("author", EmbeddedModelField("testapp.author")),
                    ],
                ),
                ModelState(
                    "testapp",
                    "Author",
                    [
                        ("id", ObjectIdAutoField(primary_key=True)),
                        ("name", models.CharField(max_length=10)),
                    ],
                    {"managed": False},
                ),
            ],
            [
                ModelState(
                    "testapp",
                    "Book",
                    [
                        ("id", ObjectIdAutoField(primary_key=True)),
                        ("name", models.CharField(max_length=200)),
                        ("author", EmbeddedModelField("testapp.author")),
                    ],
                ),
                ModelState(
                    "testapp",
                    "Author",
                    [
                        ("id", ObjectIdAutoField(primary_key=True)),
                        ("name", models.CharField(max_length=10, db_column="the_name")),
                    ],
                    {"managed": False},
                ),
            ],
        )
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(changes, "testapp", 0, ["AlterField", "AlterEmbeddedField"])
        self.assertOperationAttributes(changes, "testapp", 0, 0, model_name="author", name="name")
        self.assertOperationAttributes(
            changes, "testapp", 0, 1, model_name="book", name="author.name"
        )

    def test_rename_embedded_field(self):
        """
        Detection of renamed embedded fields (Author.name -> Author.full_name).
        """
        changes = self.get_changes(
            [
                ModelState(
                    "testapp",
                    "Book",
                    [
                        ("id", ObjectIdAutoField(primary_key=True)),
                        ("name", models.CharField(max_length=200)),
                        ("author", EmbeddedModelField("testapp.author")),
                    ],
                ),
                ModelState(
                    "testapp",
                    "Author",
                    [
                        ("id", ObjectIdAutoField(primary_key=True)),
                        ("name", models.CharField(max_length=10)),
                    ],
                    {"managed": False},
                ),
            ],
            [
                ModelState(
                    "testapp",
                    "Book",
                    [
                        ("id", ObjectIdAutoField(primary_key=True)),
                        ("name", models.CharField(max_length=200)),
                        ("author", EmbeddedModelField("testapp.author")),
                    ],
                ),
                ModelState(
                    "testapp",
                    "Author",
                    [
                        ("id", ObjectIdAutoField(primary_key=True)),
                        ("full_name", models.CharField(max_length=10)),
                    ],
                    {"managed": False},
                ),
            ],
            MigrationQuestioner({"ask_rename": True}),
        )
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(changes, "testapp", 0, ["RenameField", "RenameEmbeddedField"])
        self.assertOperationAttributes(
            changes, "testapp", 0, 0, model_name="author", old_name="name", new_name="full_name"
        )
        self.assertOperationAttributes(
            changes,
            "testapp",
            0,
            1,
            model_name="book",
            old_name="author.name",
            new_name="author.full_name",
        )

    def test_alter_embbedded_field_max_length(self):
        """AlterEmbeddedField isn't generated for max_length changes."""
        changes = self.get_changes(
            [
                ModelState(
                    "testapp",
                    "Book",
                    [
                        ("id", ObjectIdAutoField(primary_key=True)),
                        ("name", models.CharField(max_length=200)),
                        ("author", EmbeddedModelField("testapp.author")),
                    ],
                ),
                ModelState(
                    "testapp",
                    "Author",
                    [
                        ("id", ObjectIdAutoField(primary_key=True)),
                        ("name", models.CharField(max_length=10)),
                    ],
                    {"managed": False},
                ),
            ],
            [
                ModelState(
                    "testapp",
                    "Book",
                    [
                        ("id", ObjectIdAutoField(primary_key=True)),
                        ("name", models.CharField(max_length=200)),
                        ("author", EmbeddedModelField("testapp.author")),
                    ],
                ),
                ModelState(
                    "testapp",
                    "Author",
                    [
                        ("id", ObjectIdAutoField(primary_key=True)),
                        ("name", models.CharField(max_length=15)),  # max_length increased
                    ],
                    {"managed": False},
                ),
            ],
        )
        self.assertNumberMigrations(changes, "testapp", 1)
        # No AlterEmbeddedField operation generated.
        self.assertOperationTypes(changes, "testapp", 0, ["AlterField"])
        self.assertOperationAttributes(changes, "testapp", 0, 0, model_name="author", name="name")

    @mock.patch(
        "django.db.migrations.questioner.MigrationQuestioner.ask_not_null_alteration",
        side_effect=AssertionError("Should not have prompted for not null alteration"),
    )
    def test_alter_field_to_not_null_with_default(self, mocked_ask_method):
        """
        Nullable to non-nullable alteration with a default doesn't prompt.
        """
        before = [
            ModelState(
                "testapp",
                "Book",
                [
                    ("id", ObjectIdAutoField(primary_key=True)),
                    ("author", EmbeddedModelField("testapp.author")),
                ],
            ),
            ModelState(
                "testapp",
                "Author",
                [
                    ("id", ObjectIdAutoField(primary_key=True)),
                    ("name", models.CharField(max_length=10, null=True)),
                ],
                {"managed": False},
            ),
        ]
        after = [
            ModelState(
                "testapp",
                "Book",
                [
                    ("id", ObjectIdAutoField(primary_key=True)),
                    ("author", EmbeddedModelField("testapp.author")),
                ],
            ),
            ModelState(
                "testapp",
                "Author",
                [
                    ("id", ObjectIdAutoField(primary_key=True)),
                    ("name", models.CharField(max_length=10, default="Ada Lovelace")),
                ],
                {"managed": False},
            ),
        ]
        changes = self.get_changes(before, after)
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(changes, "testapp", 0, ["AlterField"])
        self.assertOperationAttributes(changes, "testapp", 0, 0, name="name", preserve_default=True)
        self.assertOperationFieldAttributes(changes, "testapp", 0, 0, default="Ada Lovelace")

    @mock.patch(
        "django.db.migrations.questioner.MigrationQuestioner.ask_not_null_alteration",
        return_value=models.NOT_PROVIDED,
    )
    def test_alter_field_to_not_null_without_default(self, mocked_ask_method):
        """
        Nullable to non-nullable alteration without a default prompts once.
        """
        before = [
            ModelState(
                "testapp",
                "Book",
                [
                    ("id", ObjectIdAutoField(primary_key=True)),
                    ("author", EmbeddedModelField("testapp.author")),
                ],
            ),
            ModelState(
                "testapp",
                "Author",
                [
                    ("id", ObjectIdAutoField(primary_key=True)),
                    ("name", models.CharField(max_length=10, null=True)),
                ],
                {"managed": False},
            ),
        ]
        after = [
            ModelState(
                "testapp",
                "Book",
                [
                    ("id", ObjectIdAutoField(primary_key=True)),
                    ("author", EmbeddedModelField("testapp.author")),
                ],
            ),
            ModelState(
                "testapp",
                "Author",
                [
                    ("id", ObjectIdAutoField(primary_key=True)),
                    ("name", models.CharField(max_length=10)),
                ],
                {"managed": False},
            ),
        ]
        changes = self.get_changes(before, after)
        self.assertEqual(mocked_ask_method.call_count, 1)
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(changes, "testapp", 0, ["AlterField"])
        self.assertOperationAttributes(changes, "testapp", 0, 0, name="name", preserve_default=True)
        self.assertOperationFieldAttributes(changes, "testapp", 0, 0, default=models.NOT_PROVIDED)

    @mock.patch(
        "django.db.migrations.questioner.MigrationQuestioner.ask_not_null_alteration",
        return_value="Some Name",
    )
    def test_alter_field_to_not_null_oneoff_default(self, mocked_ask_method):
        """Nullable to non-nullable alteration with a one-off default."""
        before = [
            ModelState(
                "testapp",
                "Book",
                [
                    ("id", ObjectIdAutoField(primary_key=True)),
                    ("author", EmbeddedModelField("testapp.author")),
                ],
            ),
            ModelState(
                "testapp",
                "Author",
                [
                    ("id", ObjectIdAutoField(primary_key=True)),
                    ("name", models.CharField(max_length=10, null=True)),
                ],
                {"managed": False},
            ),
        ]
        after = [
            ModelState(
                "testapp",
                "Book",
                [
                    ("id", ObjectIdAutoField(primary_key=True)),
                    ("author", EmbeddedModelField("testapp.author")),
                ],
            ),
            ModelState(
                "testapp",
                "Author",
                [
                    ("id", ObjectIdAutoField(primary_key=True)),
                    ("name", models.CharField(max_length=10)),
                ],
                {"managed": False},
            ),
        ]
        changes = self.get_changes(before, after)
        self.assertEqual(mocked_ask_method.call_count, 1)
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(changes, "testapp", 0, ["AlterField"])
        self.assertOperationAttributes(
            changes, "testapp", 0, 0, name="name", preserve_default=False
        )
        self.assertOperationFieldAttributes(changes, "testapp", 0, 0, default="Some Name")

    def test_rename_field(self):
        """
        Renaming a field in an embedded model generates RenameEmbeddedField.
        """
        changes = self.get_changes(
            [
                ModelState(
                    "testapp",
                    "Book",
                    [
                        ("id", ObjectIdAutoField(primary_key=True)),
                        ("author", EmbeddedModelField("testapp.author")),
                    ],
                ),
                ModelState(
                    "testapp",
                    "Author",
                    [
                        ("id", ObjectIdAutoField(primary_key=True)),
                        ("name", models.CharField(max_length=10)),
                    ],
                    {"managed": False},
                ),
            ],
            [
                ModelState(
                    "testapp",
                    "Book",
                    [
                        ("id", ObjectIdAutoField(primary_key=True)),
                        ("author", EmbeddedModelField("testapp.author")),
                    ],
                ),
                ModelState(
                    "testapp",
                    "Author",
                    [
                        ("id", ObjectIdAutoField(primary_key=True)),
                        ("names", models.CharField(max_length=10)),
                    ],
                    {"managed": False},
                ),
            ],
            MigrationQuestioner({"ask_rename": True}),
        )
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(changes, "testapp", 0, ["RenameField", "RenameEmbeddedField"])
        self.assertOperationAttributes(
            changes, "testapp", 0, 0, model_name="author", old_name="name", new_name="names"
        )
        self.assertOperationAttributes(
            changes,
            "testapp",
            0,
            1,
            model_name="book",
            old_name="author.name",
            new_name="author.names",
        )

    def test_rename_field_preserved_db_column(self):
        """
        RenameField is used if a field is renamed and db_column equal to the
        old field's column is added. RenameEmbeddedField is also generated
        since the attribute path changes even though the column path doesn't.
        """
        before = [
            ModelState(
                "testapp",
                "Book",
                [
                    ("id", ObjectIdAutoField(primary_key=True)),
                    ("author", EmbeddedModelField("testapp.author")),
                ],
            ),
            ModelState(
                "testapp",
                "Author",
                [
                    ("id", ObjectIdAutoField(primary_key=True)),
                    ("field", models.IntegerField()),
                ],
                {"managed": False},
            ),
        ]
        after = [
            ModelState(
                "testapp",
                "Book",
                [
                    ("id", ObjectIdAutoField(primary_key=True)),
                    ("author", EmbeddedModelField("testapp.author")),
                ],
            ),
            ModelState(
                "testapp",
                "Author",
                [
                    ("id", ObjectIdAutoField(primary_key=True)),
                    ("renamed_field", models.IntegerField(db_column="field")),
                ],
                {"managed": False},
            ),
        ]
        changes = self.get_changes(before, after, MigrationQuestioner({"ask_rename": True}))
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(
            changes, "testapp", 0, ["AlterField", "RenameField", "RenameEmbeddedField"]
        )
        self.assertOperationAttributes(
            changes,
            "testapp",
            0,
            0,
            model_name="author",
            name="field",
        )
        self.assertEqual(
            changes["testapp"][0].operations[0].field.deconstruct(),
            (
                "field",
                "django.db.models.IntegerField",
                [],
                {"db_column": "field"},
            ),
        )
        self.assertOperationAttributes(
            changes,
            "testapp",
            0,
            1,
            model_name="author",
            old_name="field",
            new_name="renamed_field",
        )
        self.assertOperationAttributes(
            changes,
            "testapp",
            0,
            2,
            model_name="book",
            old_name="author.field",
            new_name="author.renamed_field",
        )

    def test_add_field_with_default(self):
        """
        Adding a field with a default to an embedded model generates
        AddEmbeddedField.
        """
        before = [
            ModelState(
                "testapp",
                "Book",
                [
                    ("id", ObjectIdAutoField(primary_key=True)),
                    ("author", EmbeddedModelField("testapp.author")),
                ],
            ),
            ModelState(
                "testapp",
                "Author",
                [
                    ("id", ObjectIdAutoField(primary_key=True)),
                ],
                {"managed": False},
            ),
        ]
        after = [
            ModelState(
                "testapp",
                "Book",
                [
                    ("id", ObjectIdAutoField(primary_key=True)),
                    ("author", EmbeddedModelField("testapp.author")),
                ],
            ),
            ModelState(
                "testapp",
                "Author",
                [
                    ("id", ObjectIdAutoField(primary_key=True)),
                    ("name", models.CharField(max_length=10, default="Ada Lovelace")),
                ],
                {"managed": False},
            ),
        ]
        changes = self.get_changes(before, after)
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(changes, "testapp", 0, ["AddField", "AddEmbeddedField"])
        self.assertOperationAttributes(changes, "testapp", 0, 0, name="name")

    @mock.patch(
        "django.db.migrations.questioner.MigrationQuestioner.ask_not_null_addition",
        side_effect=AssertionError("Should not have prompted for not null addition"),
    )
    def test_add_blank_textfield_and_charfield(self, mocked_ask_method):
        """
        Adding a NOT NULL and blank CharField or TextField without default
        should not prompt for a default.
        """
        before = [
            ModelState(
                "testapp",
                "Book",
                [
                    ("id", ObjectIdAutoField(primary_key=True)),
                    ("author", EmbeddedModelField("testapp.author")),
                ],
            ),
            ModelState(
                "testapp",
                "Author",
                [
                    ("id", ObjectIdAutoField(primary_key=True)),
                ],
                {"managed": False},
            ),
        ]
        after = [
            ModelState(
                "testapp",
                "Book",
                [
                    ("id", ObjectIdAutoField(primary_key=True)),
                    ("author", EmbeddedModelField("testapp.author")),
                ],
            ),
            ModelState(
                "testapp",
                "Author",
                [
                    ("id", ObjectIdAutoField(primary_key=True)),
                    ("biography", models.TextField(blank=True)),
                    ("name", models.CharField(max_length=10, blank=True)),
                ],
                {"managed": False},
            ),
        ]
        changes = self.get_changes(before, after)
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(
            changes, "testapp", 0, ["AddField", "AddField", "AddEmbeddedField", "AddEmbeddedField"]
        )

    @mock.patch("django.db.migrations.questioner.MigrationQuestioner.ask_not_null_addition")
    def test_add_non_blank_textfield_and_charfield(self, mocked_ask_method):
        """
        Adding a NOT NULL and non-blank CharField or TextField without default
        prompts once per field; AddEmbeddedField reuses the same default.
        """
        before = [
            ModelState(
                "testapp",
                "Book",
                [
                    ("id", ObjectIdAutoField(primary_key=True)),
                    ("author", EmbeddedModelField("testapp.author")),
                ],
            ),
            ModelState(
                "testapp",
                "Author",
                [
                    ("id", ObjectIdAutoField(primary_key=True)),
                ],
                {"managed": False},
            ),
        ]
        after = [
            ModelState(
                "testapp",
                "Book",
                [
                    ("id", ObjectIdAutoField(primary_key=True)),
                    ("author", EmbeddedModelField("testapp.author")),
                ],
            ),
            ModelState(
                "testapp",
                "Author",
                [
                    ("id", ObjectIdAutoField(primary_key=True)),
                    ("biography", models.TextField()),
                    ("name", models.CharField(max_length=10)),
                ],
                {"managed": False},
            ),
        ]
        changes = self.get_changes(before, after)
        self.assertEqual(mocked_ask_method.call_count, 2)
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(
            changes, "testapp", 0, ["AddField", "AddField", "AddEmbeddedField", "AddEmbeddedField"]
        )
