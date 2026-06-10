from django.core.management.commands.migrate import Command as BaseCommand

from django_mongodb_backend.db.migrations.autodetector import MigrationAutodetector


class Command(BaseCommand):
    autodetector = MigrationAutodetector
