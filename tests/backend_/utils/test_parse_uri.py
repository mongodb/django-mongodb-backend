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
        # Default authSource derived from URI path db is appended to HOST
        self.assertEqual(
            settings_dict["HOST"], "cluster0.example.mongodb.net?authSource=myDatabase"
        )
        self.assertEqual(settings_dict["OPTIONS"], {})

    def test_db_name(self):
        settings_dict = parse_uri("mongodb://cluster0.example.mongodb.net/", db_name="myDatabase")
        self.assertEqual(settings_dict["ENGINE"], "django_mongodb_backend")
        self.assertEqual(settings_dict["NAME"], "myDatabase")
        self.assertEqual(settings_dict["HOST"], "cluster0.example.mongodb.net")
        # No default authSource injected when the URI has no database path
        self.assertEqual(settings_dict["OPTIONS"], {})

    def test_db_name_overrides_default_auth_db(self):
        settings_dict = parse_uri(
            "mongodb://cluster0.example.mongodb.net/default_auth_db", db_name="myDatabase"
        )
        self.assertEqual(settings_dict["ENGINE"], "django_mongodb_backend")
        self.assertEqual(settings_dict["NAME"], "myDatabase")
        # authSource defaults to the database from the URI, not db_name
        self.assertEqual(
            settings_dict["HOST"], "cluster0.example.mongodb.net?authSource=default_auth_db"
        )
        self.assertEqual(settings_dict["OPTIONS"], {})

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
        # HOST includes scheme + fqdn only (no path), with query
        # preserved and default authSource appended
        self.assertTrue(
            settings_dict["HOST"].startswith("mongodb+srv://cluster0.example.mongodb.net?")
        )
        self.assertIn("retryWrites=true", settings_dict["HOST"])
        self.assertIn("w=majority", settings_dict["HOST"])
        self.assertIn("authSource=my_database", settings_dict["HOST"])
        self.assertEqual(settings_dict["USER"], "my_user")
        self.assertEqual(settings_dict["PASSWORD"], "my_password")
        self.assertIsNone(settings_dict["PORT"])
        # No options copied into OPTIONS; they live in HOST query
        self.assertEqual(settings_dict["OPTIONS"], {})

    def test_localhost(self):
        settings_dict = parse_uri("mongodb://localhost/db")
        # Default authSource appended to HOST
        self.assertEqual(settings_dict["HOST"], "localhost?authSource=db")
        self.assertEqual(settings_dict["PORT"], 27017)

    def test_localhost_with_port(self):
        settings_dict = parse_uri("mongodb://localhost:27018/db")
        # HOST omits the path and port, keeps only host + query
        self.assertEqual(settings_dict["HOST"], "localhost?authSource=db")
        self.assertEqual(settings_dict["PORT"], 27018)

    def test_hosts_with_ports(self):
        settings_dict = parse_uri("mongodb://localhost:27017,localhost:27018/db")
        # For multi-host, PORT is None and HOST carries the full host list plus query
        self.assertEqual(settings_dict["HOST"], "localhost:27017,localhost:27018?authSource=db")
        self.assertEqual(settings_dict["PORT"], None)

    def test_hosts_without_ports(self):
        settings_dict = parse_uri("mongodb://host1.net,host2.net/db")
        # Default ports are added to each host in HOST, plus the query
        self.assertEqual(settings_dict["HOST"], "host1.net:27017,host2.net:27017?authSource=db")
        self.assertEqual(settings_dict["PORT"], None)

    def test_auth_source_in_query_string(self):
        settings_dict = parse_uri("mongodb://localhost/?authSource=auth", db_name="db")
        self.assertEqual(settings_dict["NAME"], "db")
        # Keep original query intact in HOST; do not duplicate into OPTIONS
        self.assertEqual(settings_dict["HOST"], "localhost?authSource=auth")
        self.assertEqual(settings_dict["OPTIONS"], {})

    def test_auth_source_in_query_string_overrides_defaultauthdb(self):
        settings_dict = parse_uri("mongodb://localhost/db?authSource=auth")
        self.assertEqual(settings_dict["NAME"], "db")
        # Query-provided authSource overrides default; kept in HOST only
        self.assertEqual(settings_dict["HOST"], "localhost?authSource=auth")
        self.assertEqual(settings_dict["OPTIONS"], {})

    def test_options_kwarg(self):
        options = {"authSource": "auth", "retryWrites": True}
        settings_dict = parse_uri(
            "mongodb://cluster0.example.mongodb.net/myDatabase?retryWrites=false&retryReads=true",
            options=options,
        )
        # options kwarg overrides same-key query params; query-only keys are kept.
        # All options live in HOST's query string; OPTIONS is empty.
        self.assertTrue(settings_dict["HOST"].startswith("cluster0.example.mongodb.net?"))
        self.assertIn("authSource=auth", settings_dict["HOST"])
        self.assertIn("retryWrites=true", settings_dict["HOST"])  # overridden
        self.assertIn("retryReads=true", settings_dict["HOST"])  # preserved
        self.assertEqual(settings_dict["OPTIONS"], {})

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

    def test_read_preference_tags_in_host_query_allows_mongoclient_construction(self):
        """
        Ensure readPreferenceTags preserved in the HOST query string can be parsed by
        MongoClient without raising validation errors, and result in correct tag sets.
        This verifies we no longer rely on pymongo's normalized options dict for tags.
        """
        cases = [
            (
                "mongodb://localhost/?readPreference=secondary&readPreferenceTags=dc:ny,other:sf&readPreferenceTags=dc:2,other:1",
                [{"dc": "ny", "other": "sf"}, {"dc": "2", "other": "1"}],
            ),
            (
                "mongodb://localhost/?retryWrites=true&readPreference=secondary&readPreferenceTags=nodeType:ANALYTICS&w=majority&appName=sniply-production",
                [{"nodeType": "ANALYTICS"}],
            ),
        ]

        for uri, expected_tags in cases:
            with self.subTest(uri=uri):
                # Baseline: demonstrate why relying on parsed options can be problematic.
                parsed = pymongo.uri_parser.parse_uri(uri)
                # Some PyMongo versions normalize this into a dict (invalid as a kwarg),
                # others into a list. If it's a dict, passing it as a kwarg will raise a
                # ValueError as shown in the issue.
                # We only assert no crash in our new path below; this is informational.
                if isinstance(parsed["options"].get("readPreferenceTags"), dict):
                    with self.assertRaises(ValueError):
                        pymongo.MongoClient(
                            readPreferenceTags=parsed["options"]["readPreferenceTags"]
                        )

                # New behavior: keep the raw query on HOST, not in OPTIONS.
                settings_dict = parse_uri(uri, db_name="db")
                host_with_query = settings_dict["HOST"]

                # Compose a full URI for MongoClient (non-SRV -> prepend scheme and
                # ensure "/?" before query)
                if host_with_query.startswith("mongodb+srv://"):
                    full_uri = host_with_query  # SRV already includes scheme
                else:
                    if "?" in host_with_query:
                        base, q = host_with_query.split("?", 1)
                        full_uri = f"mongodb://{base}/?{q}"
                    else:
                        full_uri = f"mongodb://{host_with_query}/"

                # Constructing MongoClient should not raise, and should reflect the read
                # preference + tags.
                client = pymongo.MongoClient(full_uri, serverSelectionTimeoutMS=1)
                try:
                    doc = client.read_preference.document
                    self.assertEqual(doc.get("mode"), "secondary")
                    self.assertEqual(doc.get("tags"), expected_tags)
                finally:
                    client.close()
