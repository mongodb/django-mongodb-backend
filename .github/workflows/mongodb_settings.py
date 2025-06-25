# Settings for django_mongodb_backend/tests when encryption isn't supported.
from django_settings import *  # noqa: F403

DATABASES["encrypted"] = {}  # noqa: F405
DATABASE_ROUTERS = ["django_mongodb_backend.routers.MongoRouter"]
