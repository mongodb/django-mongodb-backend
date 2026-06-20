from django.db import models
from django.db.migrations.questioner import MigrationQuestioner
from django.db.migrations.state import ModelState, ProjectState
from django.test import TestCase

from django_mongodb_backend.db.migrations.autodetector import MigrationAutodetector
from django_mongodb_backend.fields import (
    EmbeddedModelArrayField,
    EmbeddedModelField,
    ObjectIdAutoField,
    PolymorphicEmbeddedModelArrayField,
    PolymorphicEmbeddedModelField,
)


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


class EmbeddedModelOrderingTests(BaseAutodetectorTests):
    def test_embedded_models_created_first(self):
        """
        A model's CreateModel must be ordered after the CreateModel of any
        models it embeds. Otherwise the embedded model's string reference can't
        be resolved while a partial migration state is rendered.
        """
        # The models are passed in reverse dependency order (and the default
        # add order is alphabetical: Billing, Patient, PatientRecord) to ensure
        # the ordering comes from the embedded model dependency, not chance.
        changes = self.get_changes(
            [],
            [
                ModelState(
                    "testapp",
                    "Patient",
                    [
                        ("id", ObjectIdAutoField(primary_key=True)),
                        ("patient_record", EmbeddedModelField("testapp.PatientRecord")),
                    ],
                ),
                ModelState(
                    "testapp",
                    "PatientRecord",
                    [
                        ("id", ObjectIdAutoField(primary_key=True)),
                        ("billing", EmbeddedModelField("testapp.Billing")),
                    ],
                    {"managed": False},
                ),
                ModelState(
                    "testapp",
                    "Billing",
                    [("id", ObjectIdAutoField(primary_key=True))],
                    {"managed": False},
                ),
            ],
        )
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(
            changes, "testapp", 0, ["CreateModel", "CreateModel", "CreateModel"]
        )
        self.assertOperationAttributes(changes, "testapp", 0, 0, name="Billing")
        self.assertOperationAttributes(changes, "testapp", 0, 1, name="PatientRecord")
        self.assertOperationAttributes(changes, "testapp", 0, 2, name="Patient")

    def test_polymorphic_embedded_models_created_first(self):
        changes = self.get_changes(
            [],
            [
                ModelState(
                    "testapp",
                    "Owner",
                    [
                        ("id", ObjectIdAutoField(primary_key=True)),
                        ("pet", PolymorphicEmbeddedModelField(("testapp.Cat", "testapp.Dog"))),
                    ],
                ),
                ModelState(
                    "testapp",
                    "Cat",
                    [("id", ObjectIdAutoField(primary_key=True))],
                    {"managed": False},
                ),
                ModelState(
                    "testapp",
                    "Dog",
                    [("id", ObjectIdAutoField(primary_key=True))],
                    {"managed": False},
                ),
            ],
        )
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(
            changes, "testapp", 0, ["CreateModel", "CreateModel", "CreateModel"]
        )
        # Cat and Dog must both precede Owner.
        names = [op.name for op in changes["testapp"][0].operations]
        self.assertEqual(names[2], "Owner")
        self.assertEqual(set(names[:2]), {"Cat", "Dog"})

    def test_add_embedded_field_after_embedded_model(self):
        """
        Adding an embedded field to an existing model and creating the embedded
        model in the same migration: the embedded model's CreateModel must come
        before the AddField.
        """
        changes = self.get_changes(
            [
                ModelState(
                    "testapp",
                    "Container",
                    [("id", ObjectIdAutoField(primary_key=True))],
                ),
            ],
            [
                ModelState(
                    "testapp",
                    "Container",
                    [
                        ("id", ObjectIdAutoField(primary_key=True)),
                        ("item", EmbeddedModelField("testapp.Item")),
                    ],
                ),
                ModelState(
                    "testapp",
                    "Item",
                    [("id", ObjectIdAutoField(primary_key=True))],
                    {"managed": False},
                ),
            ],
        )
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(changes, "testapp", 0, ["CreateModel", "AddField"])
        self.assertOperationAttributes(changes, "testapp", 0, 0, name="Item")
        self.assertOperationAttributes(changes, "testapp", 0, 1, name="item")

    def test_add_embedded_field_cross_app_dependency(self):
        """
        The embedded model lives in another app, so the AddField migration
        must depend on the migration that creates it.
        """
        changes = self.get_changes(
            [
                ModelState(
                    "appa",
                    "Container",
                    [("id", ObjectIdAutoField(primary_key=True))],
                ),
            ],
            [
                ModelState(
                    "appa",
                    "Container",
                    [
                        ("id", ObjectIdAutoField(primary_key=True)),
                        ("item", EmbeddedModelField("appb.Item")),
                    ],
                ),
                ModelState(
                    "appb",
                    "Item",
                    [("id", ObjectIdAutoField(primary_key=True))],
                    {"managed": False},
                ),
            ],
        )
        self.assertNumberMigrations(changes, "appa", 1)
        self.assertNumberMigrations(changes, "appb", 1)
        self.assertOperationTypes(changes, "appa", 0, ["AddField"])
        self.assertMigrationDependencies(changes, "appa", 0, [("appb", "auto_1")])

    def test_alter_embedded_field_after_embedded_model(self):
        """
        Repointing an embedded field at a newly created model must order the
        new model's CreateModel before the AlterField.
        """
        changes = self.get_changes(
            [
                ModelState(
                    "testapp",
                    "Old",
                    [("id", ObjectIdAutoField(primary_key=True))],
                    {"managed": False},
                ),
                ModelState(
                    "testapp",
                    "Container",
                    [
                        ("id", ObjectIdAutoField(primary_key=True)),
                        ("thing", EmbeddedModelField("testapp.Old")),
                    ],
                ),
            ],
            [
                ModelState(
                    "testapp",
                    "Old",
                    [("id", ObjectIdAutoField(primary_key=True))],
                    {"managed": False},
                ),
                ModelState(
                    "testapp",
                    "New",
                    [("id", ObjectIdAutoField(primary_key=True))],
                    {"managed": False},
                ),
                ModelState(
                    "testapp",
                    "Container",
                    [
                        ("id", ObjectIdAutoField(primary_key=True)),
                        ("thing", EmbeddedModelField("testapp.New")),
                    ],
                ),
            ],
        )
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(changes, "testapp", 0, ["CreateModel", "AlterField"])
        self.assertOperationAttributes(changes, "testapp", 0, 0, name="New")
        self.assertOperationAttributes(changes, "testapp", 0, 1, name="thing")

    def test_embedded_array_models_created_first(self):
        # The models are passed in reverse dependency order (and the default
        # add order is alphabetical: Billing, Patient, PatientRecord) to ensure
        # the ordering comes from the embedded model dependency, not chance.
        changes = self.get_changes(
            [],
            [
                ModelState(
                    "testapp",
                    "Patient",
                    [
                        ("id", ObjectIdAutoField(primary_key=True)),
                        ("patient_records", EmbeddedModelArrayField("testapp.PatientRecord")),
                    ],
                ),
                ModelState(
                    "testapp",
                    "PatientRecord",
                    [
                        ("id", ObjectIdAutoField(primary_key=True)),
                        ("billings", EmbeddedModelArrayField("testapp.Billing")),
                    ],
                    {"managed": False},
                ),
                ModelState(
                    "testapp",
                    "Billing",
                    [("id", ObjectIdAutoField(primary_key=True))],
                    {"managed": False},
                ),
            ],
        )
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(
            changes, "testapp", 0, ["CreateModel", "CreateModel", "CreateModel"]
        )
        self.assertOperationAttributes(changes, "testapp", 0, 0, name="Billing")
        self.assertOperationAttributes(changes, "testapp", 0, 1, name="PatientRecord")
        self.assertOperationAttributes(changes, "testapp", 0, 2, name="Patient")

    def test_polymorphic_embedded_array_models_created_first(self):
        changes = self.get_changes(
            [],
            [
                ModelState(
                    "testapp",
                    "Owner",
                    [
                        ("id", ObjectIdAutoField(primary_key=True)),
                        (
                            "pets",
                            PolymorphicEmbeddedModelArrayField(("testapp.Cat", "testapp.Dog")),
                        ),
                    ],
                ),
                ModelState(
                    "testapp",
                    "Cat",
                    [("id", ObjectIdAutoField(primary_key=True))],
                    {"managed": False},
                ),
                ModelState(
                    "testapp",
                    "Dog",
                    [("id", ObjectIdAutoField(primary_key=True))],
                    {"managed": False},
                ),
            ],
        )
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(
            changes, "testapp", 0, ["CreateModel", "CreateModel", "CreateModel"]
        )
        # Cat and Dog must both precede Owner.
        names = [op.name for op in changes["testapp"][0].operations]
        self.assertEqual(names[2], "Owner")
        self.assertEqual(set(names[:2]), {"Cat", "Dog"})

    def test_add_embedded_array_field_after_embedded_model(self):
        """
        Adding an embedded array field to an existing model and creating the
        embedded model in the same migration: the embedded model's CreateModel
        must come before the AddField.
        """
        changes = self.get_changes(
            [
                ModelState(
                    "testapp",
                    "Container",
                    [("id", ObjectIdAutoField(primary_key=True))],
                ),
            ],
            [
                ModelState(
                    "testapp",
                    "Container",
                    [
                        ("id", ObjectIdAutoField(primary_key=True)),
                        ("items", EmbeddedModelArrayField("testapp.Item")),
                    ],
                ),
                ModelState(
                    "testapp",
                    "Item",
                    [("id", ObjectIdAutoField(primary_key=True))],
                    {"managed": False},
                ),
            ],
        )
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(changes, "testapp", 0, ["CreateModel", "AddField"])
        self.assertOperationAttributes(changes, "testapp", 0, 0, name="Item")
        self.assertOperationAttributes(changes, "testapp", 0, 1, name="items")

    def test_add_embedded_array_field_cross_app_dependency(self):
        """
        The embedded model lives in another app, so the AddField migration
        must depend on the migration that creates it.
        """
        changes = self.get_changes(
            [
                ModelState(
                    "appa",
                    "Container",
                    [("id", ObjectIdAutoField(primary_key=True))],
                ),
            ],
            [
                ModelState(
                    "appa",
                    "Container",
                    [
                        ("id", ObjectIdAutoField(primary_key=True)),
                        ("items", EmbeddedModelArrayField("appb.Item")),
                    ],
                ),
                ModelState(
                    "appb",
                    "Item",
                    [("id", ObjectIdAutoField(primary_key=True))],
                    {"managed": False},
                ),
            ],
        )
        self.assertNumberMigrations(changes, "appa", 1)
        self.assertNumberMigrations(changes, "appb", 1)
        self.assertOperationTypes(changes, "appa", 0, ["AddField"])
        self.assertMigrationDependencies(changes, "appa", 0, [("appb", "auto_1")])

    def test_alter_embedded_array_field_after_embedded_model(self):
        """
        Repointing an embedded array field at a newly created model must order
        the new model's CreateModel before the AlterField.
        """
        changes = self.get_changes(
            [
                ModelState(
                    "testapp",
                    "Old",
                    [("id", ObjectIdAutoField(primary_key=True))],
                    {"managed": False},
                ),
                ModelState(
                    "testapp",
                    "Container",
                    [
                        ("id", ObjectIdAutoField(primary_key=True)),
                        ("things", EmbeddedModelArrayField("testapp.Old")),
                    ],
                ),
            ],
            [
                ModelState(
                    "testapp",
                    "Old",
                    [("id", ObjectIdAutoField(primary_key=True))],
                    {"managed": False},
                ),
                ModelState(
                    "testapp",
                    "New",
                    [("id", ObjectIdAutoField(primary_key=True))],
                    {"managed": False},
                ),
                ModelState(
                    "testapp",
                    "Container",
                    [
                        ("id", ObjectIdAutoField(primary_key=True)),
                        ("things", EmbeddedModelArrayField("testapp.New")),
                    ],
                ),
            ],
        )
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(changes, "testapp", 0, ["CreateModel", "AlterField"])
        self.assertOperationAttributes(changes, "testapp", 0, 0, name="New")
        self.assertOperationAttributes(changes, "testapp", 0, 1, name="things")
