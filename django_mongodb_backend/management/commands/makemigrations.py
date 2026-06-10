from django.core.management.commands.makemigrations import Command as BaseCommand

from django_mongodb_backend.db.migrations.autodetector import MigrationAutodetector


class Command(BaseCommand):
    autodetector = MigrationAutodetector
