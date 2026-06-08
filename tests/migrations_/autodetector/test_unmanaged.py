from django.db import models
from django.db.migrations.questioner import MigrationQuestioner
from django.db.migrations.state import ModelState

from .base import BaseAutodetectorTests


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
