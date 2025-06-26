from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase
from pymongo.write_concern import WriteConcern

from django_mongodb_backend.base import DatabaseWrapper


class WriteConcerrTests(TestCase):
    def test_parse_write_concern_dict(self):
        """Test parsing write concern from dictionary configuration."""
        settings_dict = {
            'NAME': 'test_db',
            'OPTIONS': {
                'WRITE_CONCERN': {'w': 'majority', 'j': True, 'wtimeout': 5000}
            }
        }
        wrapper = DatabaseWrapper(settings_dict)
        
        self.assertIsInstance(wrapper._write_concern, WriteConcern)
        self.assertIsNotNone(wrapper._write_concern)
        self.assertEqual(wrapper._write_concern.document['w'], 'majority')
        self.assertEqual(wrapper._write_concern.document['j'], True)
        self.assertEqual(wrapper._write_concern.document['wtimeout'], 5000)

    def test_parse_write_concern_string(self):
        """Test parsing write concern from string configuration."""
        settings_dict = {
            'NAME': 'test_db',
            'OPTIONS': {
                'WRITE_CONCERN': 'majority'
            }
        }
        wrapper = DatabaseWrapper(settings_dict)
        
        self.assertIsInstance(wrapper._write_concern, WriteConcern)
        self.assertIsNotNone(wrapper._write_concern)
        self.assertEqual(wrapper._write_concern.document['w'], 'majority')

    def test_parse_write_concern_int(self):
        """Test parsing write concern from integer configuration."""
        settings_dict = {
            'NAME': 'test_db',
            'OPTIONS': {
                'WRITE_CONCERN': 2
            }
        }
        wrapper = DatabaseWrapper(settings_dict)
        
        self.assertIsInstance(wrapper._write_concern, WriteConcern)
        self.assertIsNotNone(wrapper._write_concern)
        self.assertEqual(wrapper._write_concern.document['w'], 2)

    def test_parse_write_concern_none(self):
        """Test that None write concern config results in None."""
        settings_dict = {
            'NAME': 'test_db',
            'OPTIONS': {}
        }
        wrapper = DatabaseWrapper(settings_dict)
        
        self.assertIsNone(wrapper._write_concern)

    def test_parse_write_concern_invalid_type(self):
        """Test that invalid write concern type raises ImproperlyConfigured."""
        settings_dict = {
            'NAME': 'test_db',
            'OPTIONS': {
                'WRITE_CONCERN': ['invalid', 'type']
            }
        }
        
        with self.assertRaises(ImproperlyConfigured):
            DatabaseWrapper(settings_dict) 