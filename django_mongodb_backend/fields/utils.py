from django.db import connections


def get_mongodb_connection():
    for alias in connections:
        if connections[alias].vendor == "mongodb":
            return connections[alias]
    return None
