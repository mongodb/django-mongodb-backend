from bson import ObjectId
from django.urls import register_converter


class ObjectIdConverter:
    regex = "[a-f0-9]{24}"

    def to_python(self, value):
        return ObjectId(value)

    def to_url(self, value):
        return str(value)


def register_urls():
    register_converter(ObjectIdConverter, "object_id")
