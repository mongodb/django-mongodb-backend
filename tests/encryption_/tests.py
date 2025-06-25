from django.test import TestCase

from .models import Person


class EncryptedModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.objs = [Person.objects.create()]

    def test_encrypted_fields_map_on_class(self):
        expected = {
            "fields": {
                "ssn": "EncryptedCharField",
            }
        }
        self.assertEqual(Person.encrypted_fields_map, expected)

    def test_encrypted_fields_map_on_instance(self):
        instance = Person(ssn="123-45-6789")
        expected = {
            "fields": {
                "ssn": "EncryptedCharField",
            }
        }
        self.assertEqual(instance.encrypted_fields_map, expected)

    def test_non_encrypted_fields_not_included(self):
        encrypted_field_names = Person.encrypted_fields_map.keys()
        self.assertNotIn("ssn", encrypted_field_names)
