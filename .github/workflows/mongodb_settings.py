# Settings for django_mongodb_backend/tests.
from django_settings import *  # noqa: F403

DATABASE_ROUTERS = ["django_mongodb_backend.routers.MongoRouter"]
