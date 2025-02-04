from django.conf import settings
from django.core.cache import caches
from django.core.management.base import BaseCommand
from django.db import (
    DEFAULT_DB_ALIAS,
    connections,
    router,
)

from django_mongodb_backend.cache import BaseDatabaseCache, MongoDBCache


class Command(BaseCommand):
    help = "Creates the collections needed to use the MongoDB cache backend."

    requires_system_checks = []

    def add_arguments(self, parser):
        parser.add_argument(
            "args",
            metavar="collection_name",
            nargs="*",
            help=(
                "Optional collections names. Otherwise, settings.CACHES is used to find "
                "cache collections."
            ),
        )
        parser.add_argument(
            "--database",
            default=DEFAULT_DB_ALIAS,
            help="Nominates a database onto which the cache collections will be "
            'installed. Defaults to the "default" database.',
        )

        # parser.add_argument(
        #     "--dry-run",
        #     action="store_true",
        #     help="Does not create the table, just prints the SQL that would be run.",
        # )

    def handle(self, *collection_names, **options):
        db = options["database"]
        self.verbosity = options["verbosity"]
        # dry_run = options["dry_run"]
        if collection_names:
            # Legacy behavior, collection_name specified as argument
            for collection_name in collection_names:
                self.check_collection(db, collection_name)
        else:
            for cache_alias in settings.CACHES:
                cache = caches[cache_alias]
                if isinstance(cache, BaseDatabaseCache):
                    self.check_collection(db, cache._collection_name)

    def check_collection(self, database, collection_name):
        cache = MongoDBCache(collection_name, {})
        if not router.allow_migrate_model(database, cache.cache_model_class):
            return
        connection = connections[database]

        if collection_name in connection.introspection.table_names():
            if self.verbosity > 0:
                self.stdout.write("Cache table '%s' already exists." % collection_name)
            return
        cache.create_indexes()
