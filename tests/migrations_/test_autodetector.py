"""Copied from Django... to be minimized"""

from unittest import mock

from django.contrib.auth.models import AbstractBaseUser
from django.db import models
from django.db.migrations.autodetector import MigrationAutodetector
from django.db.migrations.questioner import MigrationQuestioner
from django.db.migrations.state import ModelState, ProjectState
from django.test import TestCase

from django_mongodb_backend.fields import EmbeddedModelField, ObjectIdAutoField
from django_mongodb_backend.models import EMBEDDED


class BaseAutodetectorTests(TestCase):
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


class AutodetectorTests(BaseAutodetectorTests):
    """
    Tests the migration autodetector.
    """

    author_empty = ModelState("testapp", "Author", [("id", models.AutoField(primary_key=True))])
    author_name = ModelState(
        "testapp",
        "Author",
        [
            ("id", models.AutoField(primary_key=True)),
            ("name", models.CharField(max_length=200)),
        ],
    )
    author_name_null = ModelState(
        "testapp",
        "Author",
        [
            ("id", models.AutoField(primary_key=True)),
            ("name", models.CharField(max_length=200, null=True)),
        ],
    )
    author_name_longer = ModelState(
        "testapp",
        "Author",
        [
            ("id", models.AutoField(primary_key=True)),
            ("name", models.CharField(max_length=400)),
        ],
    )
    author_name_renamed = ModelState(
        "testapp",
        "Author",
        [
            ("id", models.AutoField(primary_key=True)),
            ("names", models.CharField(max_length=200)),
        ],
    )
    author_name_default = ModelState(
        "testapp",
        "Author",
        [
            ("id", models.AutoField(primary_key=True)),
            ("name", models.CharField(max_length=200, default="Ada Lovelace")),
        ],
    )
    author_name_check_constraint = ModelState(
        "testapp",
        "Author",
        [
            ("id", models.AutoField(primary_key=True)),
            ("name", models.CharField(max_length=200)),
        ],
        {
            "constraints": [
                models.CheckConstraint(
                    condition=models.Q(name__contains="Bob"), name="name_contains_bob"
                )
            ]
        },
    )
    author_dates_of_birth_auto_now = ModelState(
        "testapp",
        "Author",
        [
            ("id", models.AutoField(primary_key=True)),
            ("date_of_birth", models.DateField(auto_now=True)),
            ("date_time_of_birth", models.DateTimeField(auto_now=True)),
            ("time_of_birth", models.TimeField(auto_now=True)),
        ],
    )
    author_dates_of_birth_auto_now_add = ModelState(
        "testapp",
        "Author",
        [
            ("id", models.AutoField(primary_key=True)),
            ("date_of_birth", models.DateField(auto_now_add=True)),
            ("date_time_of_birth", models.DateTimeField(auto_now_add=True)),
            ("time_of_birth", models.TimeField(auto_now_add=True)),
        ],
    )
    author_name_deconstructible_3 = ModelState(
        "testapp",
        "Author",
        [
            ("id", models.AutoField(primary_key=True)),
            ("name", models.CharField(max_length=200, default=models.IntegerField())),
        ],
    )
    author_name_deconstructible_4 = ModelState(
        "testapp",
        "Author",
        [
            ("id", models.AutoField(primary_key=True)),
            ("name", models.CharField(max_length=200, default=models.IntegerField())),
        ],
    )
    author_custom_pk = ModelState(
        "testapp", "Author", [("pk_field", models.IntegerField(primary_key=True))]
    )
    author_with_biography_non_blank = ModelState(
        "testapp",
        "Author",
        [
            ("id", models.AutoField(primary_key=True)),
            ("name", models.CharField()),
            ("biography", models.TextField()),
        ],
    )
    author_with_biography_blank = ModelState(
        "testapp",
        "Author",
        [
            ("id", models.AutoField(primary_key=True)),
            ("name", models.CharField(blank=True)),
            ("biography", models.TextField(blank=True)),
        ],
    )
    author_with_book = ModelState(
        "testapp",
        "Author",
        [
            ("id", models.AutoField(primary_key=True)),
            ("name", models.CharField(max_length=200)),
            ("book", models.ForeignKey("otherapp.Book", models.CASCADE)),
        ],
    )
    author_with_book_order_wrt = ModelState(
        "testapp",
        "Author",
        [
            ("id", models.AutoField(primary_key=True)),
            ("name", models.CharField(max_length=200)),
            ("book", models.ForeignKey("otherapp.Book", models.CASCADE)),
        ],
        options={"order_with_respect_to": "book"},
    )
    author_renamed_with_book = ModelState(
        "testapp",
        "Writer",
        [
            ("id", models.AutoField(primary_key=True)),
            ("name", models.CharField(max_length=200)),
            ("book", models.ForeignKey("otherapp.Book", models.CASCADE)),
        ],
    )
    author_with_publisher_string = ModelState(
        "testapp",
        "Author",
        [
            ("id", models.AutoField(primary_key=True)),
            ("name", models.CharField(max_length=200)),
            ("publisher_name", models.CharField(max_length=200)),
        ],
    )
    author_with_publisher = ModelState(
        "testapp",
        "Author",
        [
            ("id", models.AutoField(primary_key=True)),
            ("name", models.CharField(max_length=200)),
            ("publisher", models.ForeignKey("testapp.Publisher", models.CASCADE)),
        ],
    )
    author_with_user = ModelState(
        "testapp",
        "Author",
        [
            ("id", models.AutoField(primary_key=True)),
            ("name", models.CharField(max_length=200)),
            ("user", models.ForeignKey("auth.User", models.CASCADE)),
        ],
    )
    author_with_custom_user = ModelState(
        "testapp",
        "Author",
        [
            ("id", models.AutoField(primary_key=True)),
            ("name", models.CharField(max_length=200)),
            ("user", models.ForeignKey("thirdapp.CustomUser", models.CASCADE)),
        ],
    )
    author_unmanaged = ModelState(
        "testapp", "AuthorUnmanaged", [], {"managed": False}, ("testapp.author",)
    )
    author_unmanaged_managed = ModelState("testapp", "AuthorUnmanaged", [], {}, ("testapp.author",))
    author_unmanaged_default_pk = ModelState(
        "testapp", "Author", [("id", models.AutoField(primary_key=True))]
    )
    author_unmanaged_custom_pk = ModelState(
        "testapp",
        "Author",
        [
            ("pk_field", models.IntegerField(primary_key=True)),
        ],
    )
    author_with_m2m = ModelState(
        "testapp",
        "Author",
        [
            ("id", models.AutoField(primary_key=True)),
            ("publishers", models.ManyToManyField("testapp.Publisher")),
        ],
    )
    author_with_m2m_blank = ModelState(
        "testapp",
        "Author",
        [
            ("id", models.AutoField(primary_key=True)),
            ("publishers", models.ManyToManyField("testapp.Publisher", blank=True)),
        ],
    )
    other_publisher = ModelState(
        "testapp",
        "OtherPublisher",
        [
            ("id", models.AutoField(primary_key=True)),
        ],
    )
    author_with_m2m_through = ModelState(
        "testapp",
        "Author",
        [
            ("id", models.AutoField(primary_key=True)),
            (
                "publishers",
                models.ManyToManyField("testapp.Publisher", through="testapp.Contract"),
            ),
        ],
    )
    author_with_renamed_m2m_through = ModelState(
        "testapp",
        "Author",
        [
            ("id", models.AutoField(primary_key=True)),
            (
                "publishers",
                models.ManyToManyField("testapp.Publisher", through="testapp.Deal"),
            ),
        ],
    )
    author_with_former_m2m = ModelState(
        "testapp",
        "Author",
        [
            ("id", models.AutoField(primary_key=True)),
            ("publishers", models.CharField(max_length=100)),
        ],
    )
    author_with_options = ModelState(
        "testapp",
        "Author",
        [
            ("id", models.AutoField(primary_key=True)),
        ],
        {
            "permissions": [("can_hire", "Can hire")],
            "verbose_name": "Authi",
        },
    )
    author_with_db_table_comment = ModelState(
        "testapp",
        "Author",
        [
            ("id", models.AutoField(primary_key=True)),
        ],
        {"db_table_comment": "Table comment"},
    )
    author_with_db_table_options = ModelState(
        "testapp",
        "Author",
        [
            ("id", models.AutoField(primary_key=True)),
        ],
        {"db_table": "author_one"},
    )
    author_with_new_db_table_options = ModelState(
        "testapp",
        "Author",
        [
            ("id", models.AutoField(primary_key=True)),
        ],
        {"db_table": "author_two"},
    )
    author_renamed_with_db_table_options = ModelState(
        "testapp",
        "NewAuthor",
        [
            ("id", models.AutoField(primary_key=True)),
        ],
        {"db_table": "author_one"},
    )
    author_renamed_with_new_db_table_options = ModelState(
        "testapp",
        "NewAuthor",
        [
            ("id", models.AutoField(primary_key=True)),
        ],
        {"db_table": "author_three"},
    )
    contract = ModelState(
        "testapp",
        "Contract",
        [
            ("id", models.AutoField(primary_key=True)),
            ("author", models.ForeignKey("testapp.Author", models.CASCADE)),
            ("publisher", models.ForeignKey("testapp.Publisher", models.CASCADE)),
        ],
    )
    contract_renamed = ModelState(
        "testapp",
        "Deal",
        [
            ("id", models.AutoField(primary_key=True)),
            ("author", models.ForeignKey("testapp.Author", models.CASCADE)),
            ("publisher", models.ForeignKey("testapp.Publisher", models.CASCADE)),
        ],
    )
    other_pony = ModelState(
        "otherapp",
        "Pony",
        [
            ("id", models.AutoField(primary_key=True)),
        ],
    )
    other_stable = ModelState("otherapp", "Stable", [("id", models.AutoField(primary_key=True))])
    third_thing = ModelState("thirdapp", "Thing", [("id", models.AutoField(primary_key=True))])
    book = ModelState(
        "otherapp",
        "Book",
        [
            ("id", models.AutoField(primary_key=True)),
            ("author", models.ForeignKey("testapp.Author", models.CASCADE)),
            ("title", models.CharField(max_length=200)),
        ],
    )
    book_migrations_fk = ModelState(
        "otherapp",
        "Book",
        [
            ("id", models.AutoField(primary_key=True)),
            ("author", models.ForeignKey("migrations.UnmigratedModel", models.CASCADE)),
            ("title", models.CharField(max_length=200)),
        ],
    )
    book_with_no_author_fk = ModelState(
        "otherapp",
        "Book",
        [
            ("id", models.AutoField(primary_key=True)),
            ("author", models.IntegerField()),
            ("title", models.CharField(max_length=200)),
        ],
    )
    book_with_no_author = ModelState(
        "otherapp",
        "Book",
        [
            ("id", models.AutoField(primary_key=True)),
            ("title", models.CharField(max_length=200)),
        ],
    )
    book_with_author_renamed = ModelState(
        "otherapp",
        "Book",
        [
            ("id", models.AutoField(primary_key=True)),
            ("author", models.ForeignKey("testapp.Writer", models.CASCADE)),
            ("title", models.CharField(max_length=200)),
        ],
    )
    book_with_field_and_author_renamed = ModelState(
        "otherapp",
        "Book",
        [
            ("id", models.AutoField(primary_key=True)),
            ("writer", models.ForeignKey("testapp.Writer", models.CASCADE)),
            ("title", models.CharField(max_length=200)),
        ],
    )
    book_with_multiple_authors = ModelState(
        "otherapp",
        "Book",
        [
            ("id", models.AutoField(primary_key=True)),
            ("authors", models.ManyToManyField("testapp.Author")),
            ("title", models.CharField(max_length=200)),
        ],
    )
    book_with_multiple_authors_through_attribution = ModelState(
        "otherapp",
        "Book",
        [
            ("id", models.AutoField(primary_key=True)),
            (
                "authors",
                models.ManyToManyField("testapp.Author", through="otherapp.Attribution"),
            ),
            ("title", models.CharField(max_length=200)),
        ],
    )
    book_indexes = ModelState(
        "otherapp",
        "Book",
        [
            ("id", models.AutoField(primary_key=True)),
            ("author", models.ForeignKey("testapp.Author", models.CASCADE)),
            ("title", models.CharField(max_length=200)),
        ],
        {
            "indexes": [models.Index(fields=["author", "title"], name="book_title_author_idx")],
        },
    )
    book_unordered_indexes = ModelState(
        "otherapp",
        "Book",
        [
            ("id", models.AutoField(primary_key=True)),
            ("author", models.ForeignKey("testapp.Author", models.CASCADE)),
            ("title", models.CharField(max_length=200)),
        ],
        {
            "indexes": [models.Index(fields=["title", "author"], name="book_author_title_idx")],
        },
    )
    book_unique_together = ModelState(
        "otherapp",
        "Book",
        [
            ("id", models.AutoField(primary_key=True)),
            ("author", models.ForeignKey("testapp.Author", models.CASCADE)),
            ("title", models.CharField(max_length=200)),
        ],
        {
            "unique_together": {("author", "title")},
        },
    )
    book_unique_together_2 = ModelState(
        "otherapp",
        "Book",
        [
            ("id", models.AutoField(primary_key=True)),
            ("author", models.ForeignKey("testapp.Author", models.CASCADE)),
            ("title", models.CharField(max_length=200)),
        ],
        {
            "unique_together": {("title", "author")},
        },
    )
    book_unique_together_3 = ModelState(
        "otherapp",
        "Book",
        [
            ("id", models.AutoField(primary_key=True)),
            ("newfield", models.IntegerField()),
            ("author", models.ForeignKey("testapp.Author", models.CASCADE)),
            ("title", models.CharField(max_length=200)),
        ],
        {
            "unique_together": {("title", "newfield")},
        },
    )
    book_unique_together_4 = ModelState(
        "otherapp",
        "Book",
        [
            ("id", models.AutoField(primary_key=True)),
            ("newfield2", models.IntegerField()),
            ("author", models.ForeignKey("testapp.Author", models.CASCADE)),
            ("title", models.CharField(max_length=200)),
        ],
        {
            "unique_together": {("title", "newfield2")},
        },
    )
    attribution = ModelState(
        "otherapp",
        "Attribution",
        [
            ("id", models.AutoField(primary_key=True)),
            ("author", models.ForeignKey("testapp.Author", models.CASCADE)),
            ("book", models.ForeignKey("otherapp.Book", models.CASCADE)),
        ],
    )
    edition = ModelState(
        "thirdapp",
        "Edition",
        [
            ("id", models.AutoField(primary_key=True)),
            ("book", models.ForeignKey("otherapp.Book", models.CASCADE)),
        ],
    )
    custom_user = ModelState(
        "thirdapp",
        "CustomUser",
        [
            ("id", models.AutoField(primary_key=True)),
            ("username", models.CharField(max_length=255)),
        ],
        bases=(AbstractBaseUser,),
    )
    custom_user_no_inherit = ModelState(
        "thirdapp",
        "CustomUser",
        [
            ("id", models.AutoField(primary_key=True)),
            ("username", models.CharField(max_length=255)),
        ],
    )
    aardvark = ModelState("thirdapp", "Aardvark", [("id", models.AutoField(primary_key=True))])
    aardvark_testapp = ModelState(
        "testapp", "Aardvark", [("id", models.AutoField(primary_key=True))]
    )
    aardvark_based_on_author = ModelState("testapp", "Aardvark", [], bases=("testapp.Author",))
    aardvark_pk_fk_author = ModelState(
        "testapp",
        "Aardvark",
        [
            (
                "id",
                models.OneToOneField("testapp.Author", models.CASCADE, primary_key=True),
            ),
        ],
    )
    knight = ModelState("eggs", "Knight", [("id", models.AutoField(primary_key=True))])
    rabbit = ModelState(
        "eggs",
        "Rabbit",
        [
            ("id", models.AutoField(primary_key=True)),
            ("knight", models.ForeignKey("eggs.Knight", models.CASCADE)),
            ("parent", models.ForeignKey("eggs.Rabbit", models.CASCADE)),
        ],
        {
            "unique_together": {("parent", "knight")},
            "indexes": [models.Index(fields=["parent", "knight"], name="rabbit_circular_fk_index")],
        },
    )

    def test_old_model(self):
        """Tests deletion of old models."""
        changes = self.get_changes([self.author_empty], [])
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(changes, "testapp", 0, ["DeleteModel"])
        self.assertOperationAttributes(changes, "testapp", 0, 0, name="Author")

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
                    {"db_table": EMBEDDED},
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
                    {"db_table": EMBEDDED},
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
                    {"db_table": EMBEDDED},
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
                    {"db_table": EMBEDDED},
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
                    {"db_table": EMBEDDED},
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
                    {"db_table": EMBEDDED},
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
        changes = self.get_changes([self.author_empty], [self.author_dates_of_birth_auto_now_add])
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(changes, "testapp", 0, ["AddField", "AddField", "AddField"])
        self.assertOperationFieldAttributes(changes, "testapp", 0, 0, auto_now_add=True)
        self.assertOperationFieldAttributes(changes, "testapp", 0, 1, auto_now_add=True)
        self.assertOperationFieldAttributes(changes, "testapp", 0, 2, auto_now_add=True)

    @mock.patch("django.db.migrations.questioner.MigrationQuestioner.ask_auto_now_add_addition")
    def test_add_date_fields_with_auto_now_add_asking_for_default(self, mocked_ask_method):
        changes = self.get_changes([self.author_empty], [self.author_dates_of_birth_auto_now_add])
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(changes, "testapp", 0, ["AddField", "AddField", "AddField"])
        self.assertOperationFieldAttributes(changes, "testapp", 0, 0, auto_now_add=True)
        self.assertOperationFieldAttributes(changes, "testapp", 0, 1, auto_now_add=True)
        self.assertOperationFieldAttributes(changes, "testapp", 0, 2, auto_now_add=True)
        self.assertEqual(mocked_ask_method.call_count, 3)

    def test_add_embedded_model_field(self):
        """Detection of new embedded fields (Author.age)."""
        changes = self.get_changes(
            [
                ModelState(
                    "testapp",
                    "Book",
                    [
                        ("id", ObjectIdAutoField(primary_key=True)),
                        ("name", models.CharField(max_length=200)),
                        # ("author", EmbeddedModelField("testapp.author")),
                    ],
                ),
                #                ModelState(
                #                    "testapp",
                #                    "Author",
                #                    [
                #                        ("id", ObjectIdAutoField(primary_key=True)),
                #                        ("name", models.CharField(max_length=10)),
                #                    ],
                #                    {"db_table": EMBEDDED},
                #                ),
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
                    {"db_table": EMBEDDED},
                ),
            ],
        )
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(changes, "testapp", 0, ["AddField", "AddEmbeddedField"])

        # Should generate AddEmbeddedModelField for the new model and not an
        # AddEmbeddedField for each subfield.
        self.assertOperationAttributes(
            changes,
            "testapp",
            0,
            1,
            model_name="book",
            name="author.age",
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
                    {"db_table": EMBEDDED},
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
                    ],
                    {"db_table": EMBEDDED},
                ),
            ],
        )
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(changes, "testapp", 0, ["RemoveField", "RemoveEmbeddedField"])
        self.assertOperationAttributes(changes, "testapp", 0, 0, name="name")
        self.assertOperationAttributes(changes, "testapp", 0, 1, name="author.name")

    def test_alter_field(self):
        """Tests autodetection of new fields."""
        changes = self.get_changes([self.author_name], [self.author_name_longer])
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(changes, "testapp", 0, ["AlterField"])
        self.assertOperationAttributes(changes, "testapp", 0, 0, name="name", preserve_default=True)

    @mock.patch(
        "django.db.migrations.questioner.MigrationQuestioner.ask_not_null_alteration",
        side_effect=AssertionError("Should not have prompted for not null addition"),
    )
    def test_alter_field_to_not_null_with_default(self, mocked_ask_method):
        """
        Tests autodetection of nullable to non-nullable alterations.
        """
        changes = self.get_changes([self.author_name_null], [self.author_name_default])
        # Right number/type of migrations?
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
        Tests autodetection of nullable to non-nullable alterations.
        """
        changes = self.get_changes([self.author_name_null], [self.author_name])
        self.assertEqual(mocked_ask_method.call_count, 1)
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(changes, "testapp", 0, ["AlterField"])
        self.assertOperationAttributes(changes, "testapp", 0, 0, name="name", preserve_default=True)
        self.assertOperationFieldAttributes(changes, "testapp", 0, 0, default=models.NOT_PROVIDED)

    @mock.patch(
        "django.db.migrations.questioner.MigrationQuestioner.ask_not_null_alteration",
        return_value="Some Name",
    )
    def test_alter_field_to_not_null_oneoff_default(self, mocked_ask_method):
        """
        Tests autodetection of nullable to non-nullable alterations.
        """
        changes = self.get_changes([self.author_name_null], [self.author_name])
        self.assertEqual(mocked_ask_method.call_count, 1)
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(changes, "testapp", 0, ["AlterField"])
        self.assertOperationAttributes(
            changes, "testapp", 0, 0, name="name", preserve_default=False
        )
        self.assertOperationFieldAttributes(changes, "testapp", 0, 0, default="Some Name")

    def test_rename_field(self):
        """Tests autodetection of renamed fields."""
        changes = self.get_changes(
            [self.author_name],
            [self.author_name_renamed],
            MigrationQuestioner({"ask_rename": True}),
        )
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(changes, "testapp", 0, ["RenameField"])
        self.assertOperationAttributes(changes, "testapp", 0, 0, old_name="name", new_name="names")

    def test_rename_field_preserved_db_column(self):
        """
        RenameField is used if a field is renamed and db_column equal to the
        old field's column is added.
        """
        before = [
            ModelState(
                "app",
                "Foo",
                [
                    ("id", models.AutoField(primary_key=True)),
                    ("field", models.IntegerField()),
                ],
            ),
        ]
        after = [
            ModelState(
                "app",
                "Foo",
                [
                    ("id", models.AutoField(primary_key=True)),
                    ("renamed_field", models.IntegerField(db_column="field")),
                ],
            ),
        ]
        changes = self.get_changes(before, after, MigrationQuestioner({"ask_rename": True}))
        self.assertNumberMigrations(changes, "app", 1)
        self.assertOperationTypes(changes, "app", 0, ["AlterField", "RenameField"])
        self.assertOperationAttributes(
            changes,
            "app",
            0,
            0,
            model_name="foo",
            name="field",
        )
        self.assertEqual(
            changes["app"][0].operations[0].field.deconstruct(),
            (
                "field",
                "django.db.models.IntegerField",
                [],
                {"db_column": "field"},
            ),
        )
        self.assertOperationAttributes(
            changes,
            "app",
            0,
            1,
            model_name="foo",
            old_name="field",
            new_name="renamed_field",
        )

    def test_rename_field_preserve_db_column_preserve_constraint(self):
        """
        Renaming a field that already had a db_column attribute and a
        constraint generates two no-op operations: RenameField and
        AlterConstraint.
        """
        before = [
            ModelState(
                "app",
                "Foo",
                [
                    ("id", models.AutoField(primary_key=True)),
                    ("field", models.IntegerField(db_column="full_field1_name")),
                    ("field2", models.IntegerField()),
                ],
                options={
                    "constraints": [
                        models.UniqueConstraint(
                            fields=["field", "field2"],
                            name="unique_field",
                        ),
                    ],
                },
            ),
        ]
        after = [
            ModelState(
                "app",
                "Foo",
                [
                    ("id", models.AutoField(primary_key=True)),
                    (
                        "full_field1_name",
                        models.IntegerField(db_column="full_field1_name"),
                    ),
                    (
                        "field2",
                        models.IntegerField(),
                    ),
                ],
                options={
                    "constraints": [
                        models.UniqueConstraint(
                            fields=["full_field1_name", "field2"],
                            name="unique_field",
                        ),
                    ],
                },
            ),
        ]
        changes = self.get_changes(before, after, MigrationQuestioner({"ask_rename": True}))
        self.assertNumberMigrations(changes, "app", 1)
        self.assertOperationTypes(changes, "app", 0, ["RenameField", "AlterConstraint"])
        self.assertOperationAttributes(
            changes,
            "app",
            0,
            1,
            model_name="foo",
            name="unique_field",
        )
        self.assertEqual(
            changes["app"][0].operations[1].deconstruct(),
            (
                "AlterConstraint",
                [],
                {
                    "constraint": after[0].options["constraints"][0],
                    "model_name": "foo",
                    "name": "unique_field",
                },
            ),
        )

    def test_rename_field_without_db_column_recreate_constraint(self):
        """Renaming a field without given db_column recreates a constraint."""
        before = [
            ModelState(
                "app",
                "Foo",
                [
                    ("id", models.AutoField(primary_key=True)),
                    ("field", models.IntegerField()),
                ],
                options={
                    "constraints": [
                        models.UniqueConstraint(
                            fields=["field"],
                            name="unique_field",
                        ),
                    ],
                },
            ),
        ]
        after = [
            ModelState(
                "app",
                "Foo",
                [
                    ("id", models.AutoField(primary_key=True)),
                    (
                        "full_field1_name",
                        models.IntegerField(),
                    ),
                ],
                options={
                    "constraints": [
                        models.UniqueConstraint(
                            fields=["full_field1_name"],
                            name="unique_field",
                        ),
                    ],
                },
            ),
        ]
        changes = self.get_changes(before, after, MigrationQuestioner({"ask_rename": True}))
        self.assertNumberMigrations(changes, "app", 1)
        self.assertOperationTypes(
            changes, "app", 0, ["RemoveConstraint", "RenameField", "AddConstraint"]
        )

    def test_rename_field_preserve_db_column_recreate_constraint(self):
        """Removing a field from the constraint triggers recreation."""
        before = [
            ModelState(
                "app",
                "Foo",
                [
                    ("id", models.AutoField(primary_key=True)),
                    ("field1", models.IntegerField(db_column="field1")),
                    ("field2", models.IntegerField(db_column="field2")),
                ],
                options={
                    "constraints": [
                        models.UniqueConstraint(
                            fields=["field1", "field2"],
                            name="unique_fields",
                        ),
                    ],
                },
            ),
        ]
        after = [
            ModelState(
                "app",
                "Foo",
                [
                    ("id", models.AutoField(primary_key=True)),
                    ("renamed_field1", models.IntegerField(db_column="field1")),
                    ("renamed_field2", models.IntegerField(db_column="field2")),
                ],
                options={
                    "constraints": [
                        models.UniqueConstraint(
                            fields=["renamed_field1"],
                            name="unique_fields",
                        ),
                    ],
                },
            ),
        ]
        changes = self.get_changes(before, after, MigrationQuestioner({"ask_rename": True}))
        self.assertNumberMigrations(changes, "app", 1)
        self.assertOperationTypes(
            changes,
            "app",
            0,
            [
                "RemoveConstraint",
                "RenameField",
                "RenameField",
                "AddConstraint",
            ],
        )

    def test_rename_field_with_renamed_model(self):
        changes = self.get_changes(
            [self.author_name],
            [
                ModelState(
                    "testapp",
                    "RenamedAuthor",
                    [
                        ("id", models.AutoField(primary_key=True)),
                        ("renamed_name", models.CharField(max_length=200)),
                    ],
                ),
            ],
            MigrationQuestioner({"ask_rename_model": True, "ask_rename": True}),
        )
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(changes, "testapp", 0, ["RenameModel", "RenameField"])
        self.assertOperationAttributes(
            changes,
            "testapp",
            0,
            0,
            old_name="Author",
            new_name="RenamedAuthor",
        )
        self.assertOperationAttributes(
            changes,
            "testapp",
            0,
            1,
            old_name="name",
            new_name="renamed_name",
        )

    def test_rename_model(self):
        """Tests autodetection of renamed models."""
        changes = self.get_changes(
            [self.author_with_book, self.book],
            [self.author_renamed_with_book, self.book_with_author_renamed],
            MigrationQuestioner({"ask_rename_model": True}),
        )
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(changes, "testapp", 0, ["RenameModel"])
        self.assertOperationAttributes(
            changes, "testapp", 0, 0, old_name="Author", new_name="Writer"
        )
        # Now that RenameModel handles related fields too, there should be
        # no AlterField for the related field.
        self.assertNumberMigrations(changes, "otherapp", 0)

    def test_rename_model_case(self):
        """
        Model name is case-insensitive. Changing case doesn't lead to any
        autodetected operations.
        """
        author_renamed = ModelState(
            "testapp",
            "author",
            [
                ("id", models.AutoField(primary_key=True)),
            ],
        )
        changes = self.get_changes(
            [self.author_empty, self.book],
            [author_renamed, self.book],
            questioner=MigrationQuestioner({"ask_rename_model": True}),
        )
        self.assertNumberMigrations(changes, "testapp", 0)
        self.assertNumberMigrations(changes, "otherapp", 0)

    def test_remove_field_with_model_options(self):
        before_state = [
            ModelState("testapp", "Animal", []),
            ModelState(
                "testapp",
                "Dog",
                fields=[
                    ("name", models.CharField(max_length=100)),
                    (
                        "animal",
                        models.ForeignKey("testapp.Animal", on_delete=models.CASCADE),
                    ),
                ],
                options={
                    "indexes": [models.Index(fields=("animal", "name"), name="animal_name_idx")],
                    "constraints": [
                        models.UniqueConstraint(fields=("animal", "name"), name="animal_name_idx"),
                    ],
                },
            ),
        ]
        changes = self.get_changes(before_state, [])
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(
            changes,
            "testapp",
            0,
            [
                "RemoveIndex",
                "RemoveConstraint",
                "RemoveField",
                "DeleteModel",
                "DeleteModel",
            ],
        )

    def test_add_field_with_default(self):
        """#22030 - Adding a field with a default should work."""
        changes = self.get_changes([self.author_empty], [self.author_name_default])
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(changes, "testapp", 0, ["AddField"])
        self.assertOperationAttributes(changes, "testapp", 0, 0, name="name")

    @mock.patch(
        "django.db.migrations.questioner.MigrationQuestioner.ask_not_null_addition",
        side_effect=AssertionError("Should not have prompted for not null addition"),
    )
    def test_add_many_to_many(self, mocked_ask_method):
        """
        #22435 - Adding a ManyToManyField should not prompt for a default.
        """
        changes = self.get_changes(
            [self.author_empty, self.publisher], [self.author_with_m2m, self.publisher]
        )
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(changes, "testapp", 0, ["AddField"])
        self.assertOperationAttributes(changes, "testapp", 0, 0, name="publishers")

    def test_alter_many_to_many(self):
        changes = self.get_changes(
            [self.author_with_m2m, self.publisher],
            [self.author_with_m2m_blank, self.publisher],
        )
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(changes, "testapp", 0, ["AlterField"])
        self.assertOperationAttributes(changes, "testapp", 0, 0, name="publishers")

    def test_create_with_through_model(self):
        """
        Adding a m2m with a through model and the models that use it should be
        ordered correctly.
        """
        changes = self.get_changes(
            [], [self.author_with_m2m_through, self.publisher, self.contract]
        )
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(
            changes,
            "testapp",
            0,
            [
                "CreateModel",
                "CreateModel",
                "CreateModel",
                "AddField",
            ],
        )
        self.assertOperationAttributes(changes, "testapp", 0, 0, name="Author")
        self.assertOperationAttributes(changes, "testapp", 0, 1, name="Publisher")
        self.assertOperationAttributes(changes, "testapp", 0, 2, name="Contract")
        self.assertOperationAttributes(
            changes, "testapp", 0, 3, model_name="author", name="publishers"
        )

    @mock.patch(
        "django.db.migrations.questioner.MigrationQuestioner.ask_not_null_addition",
        side_effect=AssertionError("Should not have prompted for not null addition"),
    )
    def test_add_blank_textfield_and_charfield(self, mocked_ask_method):
        """
        #23405 - Adding a NOT NULL and blank `CharField` or `TextField`
        without default should not prompt for a default.
        """
        changes = self.get_changes([self.author_empty], [self.author_with_biography_blank])
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(changes, "testapp", 0, ["AddField", "AddField"])
        self.assertOperationAttributes(changes, "testapp", 0, 0)

    @mock.patch("django.db.migrations.questioner.MigrationQuestioner.ask_not_null_addition")
    def test_add_non_blank_textfield_and_charfield(self, mocked_ask_method):
        """
        #23405 - Adding a NOT NULL and non-blank `CharField` or `TextField`
        without default should prompt for a default.
        """
        changes = self.get_changes([self.author_empty], [self.author_with_biography_non_blank])
        self.assertEqual(mocked_ask_method.call_count, 2)
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(changes, "testapp", 0, ["AddField", "AddField"])
        self.assertOperationAttributes(changes, "testapp", 0, 0)

    def test_does_not_crash_after_rename_on_unique_together(self):
        fields = ("first", "second")
        before = self.make_project_state(
            [
                ModelState(
                    "app",
                    "Foo",
                    [
                        ("id", models.AutoField(primary_key=True)),
                        ("first", models.IntegerField()),
                        ("second", models.IntegerField()),
                    ],
                    options={"unique_together": {fields}},
                ),
            ]
        )
        after = before.clone()
        after.rename_field("app", "foo", "first", "first_renamed")

        changes = MigrationAutodetector(
            before, after, MigrationQuestioner({"ask_rename": True})
        )._detect_changes()

        self.assertNumberMigrations(changes, "app", 1)
        self.assertOperationTypes(changes, "app", 0, ["RenameField", "AlterUniqueTogether"])
        self.assertOperationAttributes(
            changes,
            "app",
            0,
            0,
            model_name="foo",
            old_name="first",
            new_name="first_renamed",
        )
        self.assertOperationAttributes(
            changes,
            "app",
            0,
            1,
            name="foo",
            unique_together={("first_renamed", "second")},
        )
