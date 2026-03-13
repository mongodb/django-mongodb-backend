from unittest import mock

from django.db import models
from django.db.migrations.questioner import MigrationQuestioner
from django.db.migrations.state import ModelState, ProjectState
from django.test import TestCase

from django_mongodb_backend.db.migrations.autodetector import MigrationAutodetector
from django_mongodb_backend.fields import EmbeddedModelField, ObjectIdAutoField


class BaseAutodetectorTests(TestCase):
    # Base class copied from Django's tests/migrations/test_autodetector.py.
    def repr_changes(self, changes, include_dependencies=False):
        output = ""
        for app_label, migrations_ in sorted(changes.items()):
            output += f"  {app_label}:\n"
            for migration in migrations_:
                output += f"    {migration.name}\n"
                for operation in migration.operations:
                    output += f"      {operation}\n"
                if include_dependencies:
                    output += "      Dependencies:\n"
                    if migration.dependencies:
                        for dep in migration.dependencies:
                            output += f"        {dep}\n"
                    else:
                        output += "        None\n"
        return output

    def assertNumberMigrations(self, changes, app_label, number):
        if len(changes.get(app_label, [])) != number:
            num_migrations = len(changes.get(app_label, []))
            self.fail(
                f"Incorrect number of migrations ({num_migrations}) for "
                f"{app_label} (expected {number})\n{self.repr_changes(changes)}"
            )

    def assertMigrationDependencies(self, changes, app_label, position, dependencies):
        if not changes.get(app_label):
            self.fail(f"No migrations found for {app_label}\n{self.repr_changes(changes)}")
        if len(changes[app_label]) < position + 1:
            self.fail(
                f"No migration at index {position} for {app_label}\n{self.repr_changes(changes)}"
            )
        migration = changes[app_label][position]
        if set(migration.dependencies) != set(dependencies):
            self.fail(
                f"Migration dependencies mismatch for {app_label}.{migration.name} "
                f"(expected {dependencies}):\n"
                f"{self.repr_changes(changes, include_dependencies=True)}"
            )

    def assertOperationTypes(self, changes, app_label, position, types):
        if not changes.get(app_label):
            self.fail(f"No migrations found for {app_label}\n{self.repr_changes(changes)}")
        if len(changes[app_label]) < position + 1:
            self.fail(
                f"No migration at index {position} for {app_label}\n{self.repr_changes(changes)}"
            )
        migration = changes[app_label][position]
        real_types = [operation.__class__.__name__ for operation in migration.operations]
        if types != real_types:
            self.fail(
                f"Operation type mismatch for {app_label}.{migration.name} "
                f"(expected {types}):\n{self.repr_changes(changes)}"
            )

    def assertOperationAttributes(self, changes, app_label, position, operation_position, **attrs):
        if not changes.get(app_label):
            self.fail(f"No migrations found for {app_label}\n{self.repr_changes(changes)}")
        if len(changes[app_label]) < position + 1:
            self.fail(
                f"No migration at index {position} for {app_label}\n{self.repr_changes(changes)}"
            )
        migration = changes[app_label][position]
        if len(changes[app_label]) < position + 1:
            self.fail(
                f"No operation at index {operation_position} for "
                "{app_label}.{migration.name}\n{self.repr_changes(changes)}"
            )
        operation = migration.operations[operation_position]
        for attr, value in attrs.items():
            if getattr(operation, attr, None) != value:
                self.fail(
                    f"Attribute mismatch for {app_label}.{migration.name} op "
                    f"#{operation_position}, {attr} (expected  {value!r}, got "
                    f"{getattr(operation, attr, None)!r}):\n"
                    f"{self.repr_changes(changes)}"
                )

    def assertOperationFieldAttributes(
        self, changes, app_label, position, operation_position, **attrs
    ):
        if not changes.get(app_label):
            self.fail(f"No migrations found for {app_label}\n{self.repr_changes(changes)}")
        if len(changes[app_label]) < position + 1:
            self.fail(
                f"No migration at index {position} for {app_label}\n{self.repr_changes(changes)}"
            )
        migration = changes[app_label][position]
        if len(changes[app_label]) < position + 1:
            self.fail(
                f"No operation at index {operation_position} for "
                f"{app_label}.{migration.name}\n{self.repr_changes(changes)}"
            )
        operation = migration.operations[operation_position]
        if not hasattr(operation, "field"):
            self.fail(
                f"No field attribute for {app_label}.{migration.name} op #{{operation_position}}."
            )
        field = operation.field
        for attr, value in attrs.items():
            if getattr(field, attr, None) != value:
                self.fail(
                    f"Field attribute mismatch for {app_label}.{migration.name} "
                    f"op #{operation_position}, field.{attr} (expected {value!r}, "
                    f"got {getattr(field, attr, None)!r}):\n{self.repr_changes(changes)}"
                )

    def make_project_state(self, model_states):
        "Shortcut to make ProjectStates from lists of predefined models"
        project_state = ProjectState()
        for model_state in model_states:
            project_state.add_model(model_state.clone())
        return project_state

    def get_changes(self, before_states, after_states, questioner=None):
        if not isinstance(before_states, ProjectState):
            before_states = self.make_project_state(before_states)
        if not isinstance(after_states, ProjectState):
            after_states = self.make_project_state(after_states)
        return MigrationAutodetector(
            before_states,
            after_states,
            questioner,
        )._detect_changes()


class UnmanagedModelAutodetectorTests(BaseAutodetectorTests):
    """
    Autodetection of unmanaged models. Obsolete once
    https://code.djangoproject.com/ticket/35813 is fixed.
    """

    author_unmanaged_empty = ModelState(
        "testapp",
        "Author",
        [("id", models.AutoField(primary_key=True))],
        {"managed": False},
        ("testapp.author",),
    )
    author_unmanaged_name_default = ModelState(
        "testapp",
        "Author",
        [
            ("id", models.AutoField(primary_key=True)),
            ("name", models.CharField(max_length=200, default="Ada Lovelace")),
        ],
        {"managed": False},
        ("testapp.author",),
    )
    author_unmanaged_name_longer = ModelState(
        "testapp",
        "Author",
        [
            ("id", models.AutoField(primary_key=True)),
            ("name", models.CharField(max_length=400)),
        ],
        {"managed": False},
        ("testapp.author",),
    )
    author_unmanaged_name_check_constraint = ModelState(
        "testapp",
        "Author",
        [
            ("id", models.AutoField(primary_key=True)),
            ("name", models.CharField(max_length=200, default="Ada Lovelace")),
        ],
        {
            "managed": False,
            "constraints": [
                models.CheckConstraint(
                    condition=models.Q(name__contains="Bob"), name="name_contains_bob"
                )
            ],
        },
        ("testapp.author",),
    )
    author_unmanaged_with_book = ModelState(
        "testapp",
        "Author",
        [
            ("id", models.AutoField(primary_key=True)),
            ("name", models.CharField(max_length=200)),
            ("book", models.ForeignKey("otherapp.Book", models.CASCADE)),
        ],
        {"managed": False},
        ("testapp.author",),
    )
    author_unmanaged_renamed_with_book = ModelState(
        "testapp",
        "Writer",
        [
            ("id", models.AutoField(primary_key=True)),
            ("name", models.CharField(max_length=200)),
            ("book", models.ForeignKey("otherapp.Book", models.CASCADE)),
        ],
        {"managed": False},
        ("testapp.author",),
    )
    book_unmanaged = ModelState(
        "otherapp",
        "Book",
        [
            ("id", models.AutoField(primary_key=True)),
            ("author", models.ForeignKey("testapp.Author", models.CASCADE)),
            ("title", models.CharField(max_length=200)),
        ],
        {"managed": False},
        ("otherapp.book",),
    )
    book_with_author_unmanaged_renamed = ModelState(
        "otherapp",
        "Book",
        [
            ("id", models.AutoField(primary_key=True)),
            ("author", models.ForeignKey("testapp.Writer", models.CASCADE)),
            ("title", models.CharField(max_length=200)),
        ],
        {"managed": False},
        ("otherapp.book",),
    )

    def test_unmanaged_add_field(self):
        """Tests autodetection of new fields on an unmanaged model."""
        changes = self.get_changes(
            [self.author_unmanaged_empty], [self.author_unmanaged_name_default]
        )
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(changes, "testapp", 0, ["AddField"])
        self.assertOperationAttributes(changes, "testapp", 0, 0, name="name")

    def test_unmanaged_alter_field(self):
        """Tests autodetection of altered fields on an unmanaged model."""
        changes = self.get_changes(
            [self.author_unmanaged_name_default], [self.author_unmanaged_name_longer]
        )
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(changes, "testapp", 0, ["AlterField"])
        self.assertOperationAttributes(changes, "testapp", 0, 0, name="name", preserve_default=True)

    def test_unmanaged_remove_field(self):
        """Tests autodetection of removed fields on an unmanaged model."""
        changes = self.get_changes(
            [self.author_unmanaged_name_default], [self.author_unmanaged_empty]
        )
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(changes, "testapp", 0, ["RemoveField"])
        self.assertOperationAttributes(changes, "testapp", 0, 0, name="name", model_name="author")

    def test_unmanaged_add_constraint(self):
        """Tests autodetection of new constraints on an unmanaged model."""
        changes = self.get_changes(
            [self.author_unmanaged_name_default],
            [self.author_unmanaged_name_check_constraint],
        )
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(changes, "testapp", 0, ["AddConstraint"])
        added_constraint = models.CheckConstraint(
            condition=models.Q(name__contains="Bob"), name="name_contains_bob"
        )
        self.assertOperationAttributes(
            changes, "testapp", 0, 0, model_name="author", constraint=added_constraint
        )

    def test_unmanaged_remove_constraint(self):
        """Tests autodetection of removed constraints on an unmanaged model."""
        changes = self.get_changes(
            [self.author_unmanaged_name_check_constraint],
            [self.author_unmanaged_name_default],
        )
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(changes, "testapp", 0, ["RemoveConstraint"])
        self.assertOperationAttributes(
            changes, "testapp", 0, 0, model_name="author", name="name_contains_bob"
        )

    def test_unmanaged_rename_model(self):
        """Tests autodetection of renamed unmanaged models."""
        changes = self.get_changes(
            [self.author_unmanaged_with_book, self.book_unmanaged],
            [self.author_unmanaged_renamed_with_book, self.book_with_author_unmanaged_renamed],
            MigrationQuestioner({"ask_rename_model": True}),
        )
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(changes, "testapp", 0, ["RenameModel"])
        self.assertOperationAttributes(
            changes, "testapp", 0, 0, old_name="Author", new_name="Writer"
        )
        # RenameModel handles related fields, so no AlterField needed in
        # otherapp.
        self.assertNumberMigrations(changes, "otherapp", 0)


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
        self.assertEqual(mocked_ask_method.call_count, 6)

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
        """Detection of removed nested embedded fields (Book.author.bio.title)."""
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
        """Detection of renamed embedded fields (Author.name -> Author.full_name)."""
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
        """Nullable to non-nullable alteration with a default doesn't prompt."""
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
        """Nullable to non-nullable alteration without a default prompts once."""
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
        """Renaming a field in an embedded model generates RenameEmbeddedField."""
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
        """Adding a field with a default to an embedded model generates AddEmbeddedField."""
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
        should prompt for a default (once per AddField and once per
        AddEmbeddedField).
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
        self.assertEqual(mocked_ask_method.call_count, 4)
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(
            changes, "testapp", 0, ["AddField", "AddField", "AddEmbeddedField", "AddEmbeddedField"]
        )
