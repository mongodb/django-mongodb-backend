import enum

from django.db import models

from django_mongodb_backend.fields import (
    ArrayField,
    EmbeddedModelArrayField,
    EmbeddedModelField,
    ObjectIdField,
    PolymorphicEmbeddedModelArrayField,
    PolymorphicEmbeddedModelField,
)
from django_mongodb_backend.models import EmbeddedModel


class UniqueIntegers(models.Model):
    small = models.SmallIntegerField(unique=True, blank=True, null=True)
    plain = models.IntegerField(unique=True, blank=True, null=True)
    big = models.BigIntegerField(unique=True, blank=True, null=True)
    positive_small = models.PositiveSmallIntegerField(unique=True, blank=True, null=True)
    positive = models.PositiveIntegerField(unique=True, blank=True, null=True)
    positive_big = models.PositiveBigIntegerField(unique=True, blank=True, null=True)
    duration = models.DurationField(unique=True, blank=True, null=True)


# ObjectIdField
class ObjectIdModel(models.Model):
    field = ObjectIdField()


class NullableObjectIdModel(models.Model):
    field = ObjectIdField(blank=True, null=True)


class PrimaryKeyObjectIdModel(models.Model):
    field = ObjectIdField(primary_key=True)


# ArrayField
class ArrayFieldSubclass(ArrayField):
    def __init__(self, *args, **kwargs):
        super().__init__(models.IntegerField())


class Tag:
    def __init__(self, tag_id):
        self.tag_id = tag_id

    def __eq__(self, other):
        return isinstance(other, Tag) and self.tag_id == other.tag_id

    def __hash__(self):
        return hash(self.tag_id)


class TagField(models.SmallIntegerField):
    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        return Tag(int(value))

    def to_python(self, value):
        if isinstance(value, Tag):
            return value
        if value is None:
            return value
        return Tag(int(value))

    def get_prep_value(self, value):
        return value.tag_id


class IntegerArrayModel(models.Model):
    field = ArrayField(models.IntegerField(), default=list, blank=True)


class NullableIntegerArrayModel(models.Model):
    field = ArrayField(models.IntegerField(), blank=True, null=True)
    field_nested = ArrayField(ArrayField(models.IntegerField(null=True)), null=True)
    order = models.IntegerField(null=True)

    def __str__(self):
        return str(self.field)


class CharArrayModel(models.Model):
    field = ArrayField(models.CharField(max_length=10))


class DateTimeArrayModel(models.Model):
    datetimes = ArrayField(models.DateTimeField())
    dates = ArrayField(models.DateField())
    times = ArrayField(models.TimeField())


class NestedIntegerArrayModel(models.Model):
    field = ArrayField(ArrayField(models.IntegerField()))


class OtherTypesArrayModel(models.Model):
    ips = ArrayField(models.GenericIPAddressField(), default=list)
    uuids = ArrayField(models.UUIDField(), default=list)
    decimals = ArrayField(
        models.DecimalField(max_digits=5, decimal_places=2),
        default=list,
        null=True,
        blank=True,
    )
    tags = ArrayField(TagField(), blank=True, null=True)
    json = ArrayField(models.JSONField(default=dict), default=list)


class EnumField(models.CharField):
    def get_prep_value(self, value):
        return value.value if isinstance(value, enum.Enum) else value


class ArrayEnumModel(models.Model):
    array_of_enums = ArrayField(EnumField(max_length=20))


# EmbeddedModelField
class Holder(models.Model):
    data = EmbeddedModelField("Data", null=True, blank=True)


class Data(EmbeddedModel):
    integer = models.IntegerField(db_column="custom_column")
    auto_now = models.DateTimeField(auto_now=True)
    auto_now_add = models.DateTimeField(auto_now_add=True)
    json_value = models.JSONField()
    decimal = models.DecimalField(max_digits=9, decimal_places="2", null=True, blank=True)
    nested_data = EmbeddedModelField("NestedData", null=True, blank=True)


class NestedData(EmbeddedModel):
    decimal = models.DecimalField(max_digits=9, decimal_places="2", null=True, blank=True)


class Address(EmbeddedModel):
    city = models.CharField(max_length=20)
    state = models.CharField(max_length=2)
    zip_code = models.IntegerField(db_index=True)
    tags = ArrayField(models.CharField(max_length=100), null=True, blank=True)


class Author(EmbeddedModel):
    name = models.CharField(max_length=10)
    age = models.IntegerField()
    address = EmbeddedModelField(Address)
    skills = ArrayField(models.CharField(max_length=100), null=True, blank=True)


class Book(models.Model):
    name = models.CharField(max_length=100)
    author = EmbeddedModelField(Author)


class Library(models.Model):
    name = models.CharField(max_length=100)
    books = models.ManyToManyField("Book", related_name="libraries")
    best_seller = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return self.name


# EmbeddedModelArrayField
class Movie(models.Model):
    title = models.CharField(max_length=255)
    reviews = EmbeddedModelArrayField("Review", null=True)

    def __str__(self):
        return self.title


class Review(EmbeddedModel):
    title = models.CharField(max_length=255)
    rating = models.DecimalField(max_digits=6, decimal_places=1)

    def __str__(self):
        return self.title


# An exhibit in the museum, composed of multiple sections.
class Exhibit(models.Model):
    name = models.CharField(max_length=255)
    sections = EmbeddedModelArrayField("Section", null=True)
    main_section = EmbeddedModelField("Section", null=True)

    def __str__(self):
        return self.name


# A section within an exhibit, containing multiple artifacts.
class Section(EmbeddedModel):
    number = models.IntegerField()
    artifacts = EmbeddedModelArrayField("Artifact", null=True)

    def __str__(self):
        return f"Section {self.number}"


# Details about a specific artifact.
class Artifact(EmbeddedModel):
    name = models.CharField(max_length=255)
    metadata = models.JSONField()
    restorations = EmbeddedModelArrayField("Restoration", null=True)
    last_restoration = EmbeddedModelField("Restoration", null=True)

    def __str__(self):
        return self.name


# Details about when an artifact was restored.
class Restoration(EmbeddedModel):
    date = models.DateField()
    restored_by = models.CharField(max_length=255)

    def __str__(self):
        return f"Restored by {self.restored_by} on {self.date}"


# An audit of a section in the museum.
class Audit(models.Model):
    section_number = models.IntegerField()
    reviewed = models.BooleanField()

    def __str__(self):
        return f"Section {self.section_number} audit"


# ForeignKey to a model with EmbeddedModelArrayField.
class Tour(models.Model):
    guide = models.CharField(max_length=100)
    exhibit = models.ForeignKey(Exhibit, models.CASCADE)

    def __str__(self):
        return f"Tour by {self.guide}"


# PolymorphicEmbeddedModelField
class Person(models.Model):
    name = models.CharField(max_length=100)
    pet = PolymorphicEmbeddedModelField(("Dog", "Cat"), blank=True, null=True)

    def __str__(self):
        return self.name


class Dog(EmbeddedModel):
    name = models.CharField(max_length=100)
    barks = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    favorite_toy = PolymorphicEmbeddedModelField(["Bone"], blank=True, null=True)
    toys = PolymorphicEmbeddedModelArrayField(["Bone"], blank=True, null=True)

    def __str__(self):
        return self.name


class Cat(EmbeddedModel):
    name = models.CharField(max_length=100)
    purs = models.BooleanField(default=True)
    weight = models.DecimalField(max_digits=4, decimal_places=2, blank=True, null=True)
    favorite_toy = PolymorphicEmbeddedModelField(["Mouse"], blank=True, null=True)
    toys = PolymorphicEmbeddedModelArrayField(["Mouse"], blank=True, null=True)

    def __str__(self):
        return self.name


class Bone(EmbeddedModel):
    brand = models.CharField(max_length=100)

    def __str__(self):
        return self.brand


class Mouse(EmbeddedModel):
    manufacturer = models.CharField(max_length=100)

    def __str__(self):
        return self.manufacturer


# PolymorphicEmbeddedModelArrayField
class Owner(models.Model):
    name = models.CharField(max_length=100)
    pets = PolymorphicEmbeddedModelArrayField(("Dog", "Cat"), blank=True, null=True)

    def __str__(self):
        return self.name
