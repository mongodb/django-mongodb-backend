from bson import ObjectId
from django.core import serializers
from django.test import TestCase

from .models import Address, Author, Book, Cat, Dog, Movie, Owner, Person, Review


class SerializationTests:
    maxDiff = None

    def test_embedded_model_field(self):
        objects = [
            Book(
                id=ObjectId("000000000000000000000001"),
                name="Hamlet",
                author=Author(name="Shakespeare", age=55, address=Address(city="NYC", state="NY")),
            ),
        ]
        serialized_data = serializers.serialize(self.serialization_format, objects, indent=2)
        self.assertEqual(serialized_data, self.expected_data["embedded_model_field"])
        for obj in serializers.deserialize(self.serialization_format, serialized_data):
            obj.save()
        book = Book.objects.get()
        self.assertEqual(book.name, "Hamlet")
        self.assertEqual(book.author.name, "Shakespeare")
        self.assertEqual(book.author.address.city, "NYC")

    def test_embedded_model_field_null(self):
        serialized_data = serializers.serialize(
            self.serialization_format, [Book(author=None)], indent=2
        )
        self.assertEqual(serialized_data, self.expected_data["embedded_model_field_null"])
        objs = serializers.deserialize(self.serialization_format, serialized_data)
        self.assertIsNone(next(iter(objs)).object.author, None)

    def test_embedded_model_array_field(self):
        reviews = [
            Review(title="The best", rating=10),
            Review(title="Mediocre", rating=5),
            Review(title="Horrible", rating=1),
        ]
        objects = [
            Movie(id=ObjectId("000000000000000000000001"), title="Lion King", reviews=reviews)
        ]
        serialized_data = serializers.serialize(self.serialization_format, objects, indent=2)
        self.assertEqual(serialized_data, self.expected_data["embedded_model_array_field"])
        for obj in serializers.deserialize(self.serialization_format, serialized_data):
            obj.save()
        movie = Movie.objects.get()
        self.assertEqual(movie.title, "Lion King")
        self.assertEqual(movie.reviews[0].title, "The best")
        self.assertEqual(movie.reviews[0].rating, 10)
        self.assertEqual(movie.reviews[2].title, "Horrible")
        self.assertEqual(movie.reviews[2].rating, 1)

    def test_embedded_model_array_field_null(self):
        serialized_data = serializers.serialize(
            self.serialization_format, [Movie(reviews=None)], indent=2
        )
        self.assertEqual(serialized_data, self.expected_data["embedded_model_array_field_null"])
        objs = serializers.deserialize(self.serialization_format, serialized_data)
        self.assertIsNone(next(iter(objs)).object.reviews, None)

    def test_polymorphic_embedded_model_field(self):
        objects = [
            Person(id=ObjectId("000000000000000000000001"), name="Cliff", pet=Dog(name="Woofer")),
            Person(id=ObjectId("000000000000000000000002"), name="Marla", pet=Cat(name="April")),
        ]
        serialized_data = serializers.serialize(self.serialization_format, objects, indent=2)
        self.assertEqual(serialized_data, self.expected_data["polymorphic_embedded_model_field"])
        for obj in serializers.deserialize(self.serialization_format, serialized_data):
            obj.save()
        cliff = Person.objects.get(name="Cliff")
        self.assertIsInstance(cliff.pet, Dog)
        self.assertEqual(cliff.pet.name, "Woofer")
        marla = Person.objects.get(name="Marla")
        self.assertIsInstance(marla.pet, Cat)
        self.assertEqual(marla.pet.name, "April")

    def test_polymorphic_embedded_model_field_null(self):
        serialized_data = serializers.serialize(
            self.serialization_format, [Person(pet=None)], indent=2
        )
        self.assertEqual(
            serialized_data,
            self.expected_data["polymorphic_embedded_model_field_null"],
        )
        objs = serializers.deserialize(self.serialization_format, serialized_data)
        self.assertIsNone(next(iter(objs)).object.pet, None)

    def test_polymorphic_embedded_model_array_field(self):
        objects = [
            Owner(
                id=ObjectId("000000000000000000000001"),
                name="Cliff",
                pets=[Dog(name="Woofer"), Dog(name="Joey")],
            ),
            Owner(id=ObjectId("000000000000000000000002"), name="Marla", pets=[Cat(name="April")]),
        ]
        serialized_data = serializers.serialize(self.serialization_format, objects, indent=2)
        self.assertEqual(
            serialized_data,
            self.expected_data["polymorphic_embedded_model_array_field"],
        )
        for obj in serializers.deserialize(self.serialization_format, serialized_data):
            obj.save()
        cliff = Owner.objects.get(name="Cliff")
        self.assertIsInstance(cliff.pets[0], Dog)
        self.assertEqual(cliff.pets[0].name, "Woofer")
        marla = Owner.objects.get(name="Marla")
        self.assertIsInstance(marla.pets[0], Cat)
        self.assertEqual(marla.pets[0].name, "April")

    def test_polymorphic_embedded_model_array_field_null(self):
        serialized_data = serializers.serialize(
            self.serialization_format, [Owner(pets=None)], indent=2
        )
        self.assertEqual(
            serialized_data,
            self.expected_data["polymorphic_embedded_model_array_field_null"],
        )
        objs = serializers.deserialize(self.serialization_format, serialized_data)
        self.assertIsNone(next(iter(objs)).object.pets, None)


class JSONSerializerTests(SerializationTests, TestCase):
    serialization_format = "json"
    expected_data = {
        "embedded_model_field": """[
{
  "model": "serialization_.book",
  "pk": "000000000000000000000001",
  "fields": {
    "name": "Hamlet",
    "author": {
      "id": null,
      "name": "Shakespeare",
      "age": 55,
      "address": {
        "id": null,
        "city": "NYC",
        "state": "NY",
        "zip_code": null
      }
    }
  }
}
]
""",
        "embedded_model_field_null": """[
{
  "model": "serialization_.book",
  "pk": null,
  "fields": {
    "name": "",
    "author": null
  }
}
]
""",
        "embedded_model_array_field": """[
{
  "model": "serialization_.movie",
  "pk": "000000000000000000000001",
  "fields": {
    "title": "Lion King",
    "reviews": [
      {
        "id": null,
        "title": "The best",
        "rating": 10
      },
      {
        "id": null,
        "title": "Mediocre",
        "rating": 5
      },
      {
        "id": null,
        "title": "Horrible",
        "rating": 1
      }
    ]
  }
}
]
""",
        "embedded_model_array_field_null": """[
{
  "model": "serialization_.movie",
  "pk": null,
  "fields": {
    "title": "",
    "reviews": null
  }
}
]
""",
        "polymorphic_embedded_model_field": """[
{
  "model": "serialization_.person",
  "pk": "000000000000000000000001",
  "fields": {
    "name": "Cliff",
    "pet": {
      "id": null,
      "name": "Woofer",
      "barks": true,
      "created_at": null,
      "updated_at": null,
      "favorite_toy": null,
      "toys": null,
      "_label": "serialization_.Dog"
    }
  }
},
{
  "model": "serialization_.person",
  "pk": "000000000000000000000002",
  "fields": {
    "name": "Marla",
    "pet": {
      "id": null,
      "name": "April",
      "purs": true,
      "weight": null,
      "favorite_toy": null,
      "toys": null,
      "_label": "serialization_.Cat"
    }
  }
}
]
""",
        "polymorphic_embedded_model_field_null": """[
{
  "model": "serialization_.person",
  "pk": null,
  "fields": {
    "name": "",
    "pet": null
  }
}
]
""",
        "polymorphic_embedded_model_array_field": """[
{
  "model": "serialization_.owner",
  "pk": "000000000000000000000001",
  "fields": {
    "name": "Cliff",
    "pets": [
      {
        "id": null,
        "name": "Woofer",
        "barks": true,
        "created_at": null,
        "updated_at": null,
        "favorite_toy": null,
        "toys": null,
        "_label": "serialization_.Dog"
      },
      {
        "id": null,
        "name": "Joey",
        "barks": true,
        "created_at": null,
        "updated_at": null,
        "favorite_toy": null,
        "toys": null,
        "_label": "serialization_.Dog"
      }
    ]
  }
},
{
  "model": "serialization_.owner",
  "pk": "000000000000000000000002",
  "fields": {
    "name": "Marla",
    "pets": [
      {
        "id": null,
        "name": "April",
        "purs": true,
        "weight": null,
        "favorite_toy": null,
        "toys": null,
        "_label": "serialization_.Cat"
      }
    ]
  }
}
]
""",
        "polymorphic_embedded_model_array_field_null": """[
{
  "model": "serialization_.owner",
  "pk": null,
  "fields": {
    "name": "",
    "pets": null
  }
}
]
""",
    }


class XMLSerializerTests(SerializationTests, TestCase):
    maxDiff = None
    serialization_format = "xml"
    expected_data = {
        "embedded_model_field": """<?xml version="1.0" encoding="utf-8"?>
<django-objects version="1.0">
  <object model="serialization_.book" pk="000000000000000000000001">
    <field name="name" type="CharField">Hamlet</field>
    <field name="author" type="EmbeddedModelField">
      <object model="serialization_.author">
        <field name="id" type="ObjectIdAutoField"><None></None></field>
        <field name="name" type="CharField">Shakespeare</field>
        <field name="age" type="IntegerField">55</field>
        <field name="address" type="EmbeddedModelField">
          <object model="serialization_.address">
            <field name="id" type="ObjectIdAutoField"><None></None></field>
            <field name="city" type="CharField">NYC</field>
            <field name="state" type="CharField">NY</field>
            <field name="zip_code" type="IntegerField"><None></None></field>
          </object></field>
      </object></field>
  </object>
</django-objects>""",
        "embedded_model_field_null": """<?xml version="1.0" encoding="utf-8"?>
<django-objects version="1.0">
  <object model="serialization_.book">
    <field name="name" type="CharField"></field>
    <field name="author" type="EmbeddedModelField"><None></None></field>
  </object>
</django-objects>""",
        "embedded_model_array_field": """<?xml version="1.0" encoding="utf-8"?>
<django-objects version="1.0">
  <object model="serialization_.movie" pk="000000000000000000000001">
    <field name="title" type="CharField">Lion King</field>
    <field name="reviews" type="EmbeddedModelArrayField">
      <object model="serialization_.review">
        <field name="id" type="ObjectIdAutoField"><None></None></field>
        <field name="title" type="CharField">The best</field>
        <field name="rating" type="DecimalField">10</field>
      </object>
      <object model="serialization_.review">
        <field name="id" type="ObjectIdAutoField"><None></None></field>
        <field name="title" type="CharField">Mediocre</field>
        <field name="rating" type="DecimalField">5</field>
      </object>
      <object model="serialization_.review">
        <field name="id" type="ObjectIdAutoField"><None></None></field>
        <field name="title" type="CharField">Horrible</field>
        <field name="rating" type="DecimalField">1</field>
      </object></field>
  </object>
</django-objects>""",
        "embedded_model_array_field_null": """<?xml version="1.0" encoding="utf-8"?>
<django-objects version="1.0">
  <object model="serialization_.movie">
    <field name="title" type="CharField"></field>
    <field name="reviews" type="EmbeddedModelArrayField"><None></None></field>
  </object>
</django-objects>""",
        "polymorphic_embedded_model_field": """<?xml version="1.0" encoding="utf-8"?>
<django-objects version="1.0">
  <object model="serialization_.person" pk="000000000000000000000001">
    <field name="name" type="CharField">Cliff</field>
    <field name="pet" type="PolymorphicEmbeddedModelField">
      <object model="serialization_.dog">
        <field name="id" type="ObjectIdAutoField"><None></None></field>
        <field name="name" type="CharField">Woofer</field>
        <field name="barks" type="BooleanField">True</field>
        <field name="created_at" type="DateTimeField"><None></None></field>
        <field name="updated_at" type="DateTimeField"><None></None></field>
        <field name="favorite_toy" type="PolymorphicEmbeddedModelField"><None></None></field>
        <field name="toys" type="PolymorphicEmbeddedModelArrayField"><None></None></field>
      </object></field>
  </object>
  <object model="serialization_.person" pk="000000000000000000000002">
    <field name="name" type="CharField">Marla</field>
    <field name="pet" type="PolymorphicEmbeddedModelField">
      <object model="serialization_.cat">
        <field name="id" type="ObjectIdAutoField"><None></None></field>
        <field name="name" type="CharField">April</field>
        <field name="purs" type="BooleanField">True</field>
        <field name="weight" type="DecimalField"><None></None></field>
        <field name="favorite_toy" type="PolymorphicEmbeddedModelField"><None></None></field>
        <field name="toys" type="PolymorphicEmbeddedModelArrayField"><None></None></field>
      </object></field>
  </object>
</django-objects>""",
        "polymorphic_embedded_model_field_null": """<?xml version="1.0" encoding="utf-8"?>
<django-objects version="1.0">
  <object model="serialization_.person">
    <field name="name" type="CharField"></field>
    <field name="pet" type="PolymorphicEmbeddedModelField"><None></None></field>
  </object>
</django-objects>""",
        "polymorphic_embedded_model_array_field": """<?xml version="1.0" encoding="utf-8"?>
<django-objects version="1.0">
  <object model="serialization_.owner" pk="000000000000000000000001">
    <field name="name" type="CharField">Cliff</field>
    <field name="pets" type="PolymorphicEmbeddedModelArrayField">
      <object model="serialization_.dog">
        <field name="id" type="ObjectIdAutoField"><None></None></field>
        <field name="name" type="CharField">Woofer</field>
        <field name="barks" type="BooleanField">True</field>
        <field name="created_at" type="DateTimeField"><None></None></field>
        <field name="updated_at" type="DateTimeField"><None></None></field>
        <field name="favorite_toy" type="PolymorphicEmbeddedModelField"><None></None></field>
        <field name="toys" type="PolymorphicEmbeddedModelArrayField"><None></None></field>
      </object>
      <object model="serialization_.dog">
        <field name="id" type="ObjectIdAutoField"><None></None></field>
        <field name="name" type="CharField">Joey</field>
        <field name="barks" type="BooleanField">True</field>
        <field name="created_at" type="DateTimeField"><None></None></field>
        <field name="updated_at" type="DateTimeField"><None></None></field>
        <field name="favorite_toy" type="PolymorphicEmbeddedModelField"><None></None></field>
        <field name="toys" type="PolymorphicEmbeddedModelArrayField"><None></None></field>
      </object></field>
  </object>
  <object model="serialization_.owner" pk="000000000000000000000002">
    <field name="name" type="CharField">Marla</field>
    <field name="pets" type="PolymorphicEmbeddedModelArrayField">
      <object model="serialization_.cat">
        <field name="id" type="ObjectIdAutoField"><None></None></field>
        <field name="name" type="CharField">April</field>
        <field name="purs" type="BooleanField">True</field>
        <field name="weight" type="DecimalField"><None></None></field>
        <field name="favorite_toy" type="PolymorphicEmbeddedModelField"><None></None></field>
        <field name="toys" type="PolymorphicEmbeddedModelArrayField"><None></None></field>
      </object></field>
  </object>
</django-objects>""",
        "polymorphic_embedded_model_array_field_null": """<?xml version="1.0" encoding="utf-8"?>
<django-objects version="1.0">
  <object model="serialization_.owner">
    <field name="name" type="CharField"></field>
    <field name="pets" type="PolymorphicEmbeddedModelArrayField"><None></None></field>
  </object>
</django-objects>""",
    }


class YAMLSerializerTests(SerializationTests, TestCase):
    serialization_format = "yaml"
    expected_data = {
        "embedded_model_field": """- model: serialization_.book
  pk: '000000000000000000000001'
  fields:
    name: Hamlet
    author:
      id: null
      name: Shakespeare
      age: 55
      address:
        id: null
        city: NYC
        state: NY
        zip_code: null
""",
        "embedded_model_field_null": """- model: serialization_.book
  pk: null
  fields:
    name: ''
    author: null
""",
        "embedded_model_array_field": """- model: serialization_.movie
  pk: '000000000000000000000001'
  fields:
    title: Lion King
    reviews:
    - id: null
      title: The best
      rating: 10
    - id: null
      title: Mediocre
      rating: 5
    - id: null
      title: Horrible
      rating: 1
""",
        "embedded_model_array_field_null": """- model: serialization_.movie
  pk: null
  fields:
    title: ''
    reviews: null
""",
        "polymorphic_embedded_model_field": """- model: serialization_.person
  pk: '000000000000000000000001'
  fields:
    name: Cliff
    pet:
      id: null
      name: Woofer
      barks: true
      created_at: null
      updated_at: null
      favorite_toy: null
      toys: null
      _label: serialization_.Dog
- model: serialization_.person
  pk: '000000000000000000000002'
  fields:
    name: Marla
    pet:
      id: null
      name: April
      purs: true
      weight: null
      favorite_toy: null
      toys: null
      _label: serialization_.Cat
""",
        "polymorphic_embedded_model_field_null": """- model: serialization_.person
  pk: null
  fields:
    name: ''
    pet: null
""",
        "polymorphic_embedded_model_array_field": """- model: serialization_.owner
  pk: '000000000000000000000001'
  fields:
    name: Cliff
    pets:
    - id: null
      name: Woofer
      barks: true
      created_at: null
      updated_at: null
      favorite_toy: null
      toys: null
      _label: serialization_.Dog
    - id: null
      name: Joey
      barks: true
      created_at: null
      updated_at: null
      favorite_toy: null
      toys: null
      _label: serialization_.Dog
- model: serialization_.owner
  pk: '000000000000000000000002'
  fields:
    name: Marla
    pets:
    - id: null
      name: April
      purs: true
      weight: null
      favorite_toy: null
      toys: null
      _label: serialization_.Cat
""",
        "polymorphic_embedded_model_array_field_null": """- model: serialization_.owner
  pk: null
  fields:
    name: ''
    pets: null
""",
    }
