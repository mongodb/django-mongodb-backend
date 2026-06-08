from django_mongodb_backend.rest_framework import EmbeddedModelSerializer, MongoModelSerializer

from .models import City, Continent, Country, PetOwner, StatusTag


class CitySerializer(EmbeddedModelSerializer):
    class Meta:
        model = City
        fields = "__all__"


class CountrySerializer(EmbeddedModelSerializer):
    class Meta:
        model = Country
        fields = "__all__"


class StatusTagSerializer(EmbeddedModelSerializer):
    class Meta:
        model = StatusTag
        fields = "__all__"


class ContinentSerializer(MongoModelSerializer):
    class Meta:
        model = Continent
        fields = "__all__"


class PetOwnerSerializer(MongoModelSerializer):
    class Meta:
        model = PetOwner
        fields = "__all__"
