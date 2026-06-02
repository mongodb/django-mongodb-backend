from django.test import SimpleTestCase

from django_mongodb_backend.db.migrations.autodetector import MigrationAutodetector
from django_mongodb_backend.management.commands.makemigrations import Command as MakeMigrations
from django_mongodb_backend.management.commands.migrate import Command as Migrate


class CommandTests(SimpleTestCase):
    def test_makemigrations_autodetector(self):
        self.assertIs(MakeMigrations.autodetector, MigrationAutodetector)

    def test_migrate_autodetector(self):
        self.assertIs(Migrate.autodetector, MigrationAutodetector)
