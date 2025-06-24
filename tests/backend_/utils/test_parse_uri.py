from unittest.mock import patch

import pymongo
from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase

from django_mongodb_backend import parse_uri


class ParseURITests(SimpleTestCase):
    def test_simple_uri(self):
        settings_dict = parse_uri("mongodb://cluster0.example.mongodb.net/myDatabase")
        self.assertEqual(settings_dict["ENGINE"], "django_mongodb_backend")
        self.assertEqual(settings_dict["NAME"], "myDatabase")
        self.assertEqual(settings_dict["HOST"], "cluster0.example.mongodb.net")
        self.assertEqual(settings_dict["OPTIONS"], {"authSource": "myDatabase"})

    def test_db_name(self):
        settings_dict = parse_uri("mongodb://cluster0.example.mongodb.net/", db_name="myDatabase")
        self.assertEqual(settings_dict["ENGINE"], "django_mongodb_backend")
        self.assertEqual(settings_dict["NAME"], "myDatabase")
        self.assertEqual(settings_dict["HOST"], "cluster0.example.mongodb.net")
        self.assertEqual(settings_dict["OPTIONS"], {})

    def test_db_name_overrides_default_auth_db(self):
        settings_dict = parse_uri(
            "mongodb://cluster0.example.mongodb.net/default_auth_db", db_name="myDatabase"
        )
        self.assertEqual(settings_dict["ENGINE"], "django_mongodb_backend")
        self.assertEqual(settings_dict["NAME"], "myDatabase")
        self.assertEqual(settings_dict["HOST"], "cluster0.example.mongodb.net")
        self.assertEqual(settings_dict["OPTIONS"], {"authSource": "default_auth_db"})

    def test_no_database(self):
        msg = "You must provide the db_name parameter."
        with self.assertRaisesMessage(ImproperlyConfigured, msg):
            parse_uri("mongodb://cluster0.example.mongodb.net")

    def test_srv_uri_with_options(self):
        uri = "mongodb+srv://my_user:my_password@cluster0.example.mongodb.net/my_database?retryWrites=true&w=majority"
        # patch() prevents a crash when PyMongo attempts to resolve the
        # nonexistent SRV record.
        with patch("dns.resolver.resolve"):
            settings_dict = parse_uri(uri)
        self.assertEqual(settings_dict["NAME"], "my_database")
        self.assertEqual(settings_dict["HOST"], "mongodb+srv://cluster0.example.mongodb.net")
        self.assertEqual(settings_dict["USER"], "my_user")
        self.assertEqual(settings_dict["PASSWORD"], "my_password")
        self.assertIsNone(settings_dict["PORT"])
        self.assertEqual(
            settings_dict["OPTIONS"],
            {"authSource": "my_database", "retryWrites": True, "w": "majority", "tls": True},
        )

    def test_localhost(self):
        settings_dict = parse_uri("mongodb://localhost/db")
        self.assertEqual(settings_dict["HOST"], "localhost")
        self.assertEqual(settings_dict["PORT"], 27017)

    def test_localhost_with_port(self):
        settings_dict = parse_uri("mongodb://localhost:27018/db")
        self.assertEqual(settings_dict["HOST"], "localhost")
        self.assertEqual(settings_dict["PORT"], 27018)

    def test_hosts_with_ports(self):
        settings_dict = parse_uri("mongodb://localhost:27017,localhost:27018/db")
        self.assertEqual(settings_dict["HOST"], "localhost:27017,localhost:27018")
        self.assertEqual(settings_dict["PORT"], None)

    def test_hosts_without_ports(self):
        settings_dict = parse_uri("mongodb://host1.net,host2.net/db")
        self.assertEqual(settings_dict["HOST"], "host1.net:27017,host2.net:27017")
        self.assertEqual(settings_dict["PORT"], None)

    def test_auth_source_in_query_string(self):
        settings_dict = parse_uri("mongodb://localhost/?authSource=auth", db_name="db")
        self.assertEqual(settings_dict["NAME"], "db")
        self.assertEqual(settings_dict["OPTIONS"], {"authSource": "auth"})

    def test_auth_source_in_query_string_overrides_defaultauthdb(self):
        settings_dict = parse_uri("mongodb://localhost/db?authSource=auth")
        self.assertEqual(settings_dict["NAME"], "db")
        self.assertEqual(settings_dict["OPTIONS"], {"authSource": "auth"})

    def test_options_kwarg(self):
        options = {"authSource": "auth", "retryWrites": True}
        settings_dict = parse_uri(
            "mongodb://cluster0.example.mongodb.net/myDatabase?retryWrites=false&retryReads=true",
            options=options,
        )
        self.assertEqual(
            settings_dict["OPTIONS"],
            {"authSource": "auth", "retryWrites": True, "retryReads": True},
        )

    def test_test_kwarg(self):
        settings_dict = parse_uri("mongodb://localhost/db", test={"NAME": "test_db"})
        self.assertEqual(settings_dict["TEST"], {"NAME": "test_db"})

    def test_invalid_credentials(self):
        msg = "The empty string is not valid username"
        with self.assertRaisesMessage(pymongo.errors.InvalidURI, msg):
            parse_uri("mongodb://:@localhost")

    def test_no_scheme(self):
        with self.assertRaisesMessage(pymongo.errors.InvalidURI, "Invalid URI scheme"):
            parse_uri("cluster0.example.mongodb.net")
