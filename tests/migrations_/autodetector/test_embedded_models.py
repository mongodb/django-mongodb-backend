from django.db.migrations.state import ModelState

from django_mongodb_backend.fields import (
    EmbeddedModelArrayField,
    EmbeddedModelField,
    ObjectIdAutoField,
    PolymorphicEmbeddedModelArrayField,
    PolymorphicEmbeddedModelField,
)

from .base import BaseAutodetectorTests


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
