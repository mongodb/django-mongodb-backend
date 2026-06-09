import signal
from unittest import mock

from django.db import connection
from django.test import SimpleTestCase

from django_mongodb_backend.client import DatabaseClient


class MongoDbshellTests(SimpleTestCase):
    def settings_to_cmd_args_env(self, settings_dict, parameters=None):
        if parameters is None:
            parameters = []
        return DatabaseClient.settings_to_cmd_args_env(settings_dict, parameters)

    def test_fails_with_keyerror_on_incomplete_config(self):
        with self.assertRaises(KeyError):
            self.settings_to_cmd_args_env({})

    def test_basic_params_specified_in_settings(self):
        for options_parameters in [(None, None, None), ("value1", "value2", True)]:
            with self.subTest(keys=options_parameters):
                authentication_database, authentication_mechanism, retry_writes = options_parameters
                if authentication_database is not None:
                    expected_args = [
                        "mongosh",
                        "--host",
                        "somehost",
                        "--port",
                        444,
                        "--username",
                        "someuser",
                        "--password",
                        "somepassword",
                        "--retryWrites",
                        "true",
                        "somedbname",
                    ]
                else:
                    expected_args = [
                        "mongosh",
                        "--host",
                        "somehost",
                        "--port",
                        444,
                        "--username",
                        "someuser",
                        "--password",
                        "somepassword",
                        "somedbname",
                    ]

                self.assertEqual(
                    self.settings_to_cmd_args_env(
                        {
                            "NAME": "somedbname",
                            "USER": "someuser",
                            "PASSWORD": "somepassword",
                            "HOST": "somehost",
                            "PORT": 444,
                            "OPTIONS": {
                                "authenticationDatabase": authentication_database,
                                "authenticationMechanism": authentication_mechanism,
                                "retryWrites": retry_writes,
                            },
                        }
                    ),
                    (expected_args, None),
                )

    def test_options_override_settings_proper_values(self):
        settings_port = 444
        options_port = 555
        self.assertNotEqual(settings_port, options_port, "test pre-req")
        expected_args = [
            "mongosh",
            "--host",
            "settinghost",
            "--port",
            444,
            "--username",
            "settinguser",
            "--password",
            "settingpassword",
            "settingdbname",
        ]
        expected_env = None

        self.assertEqual(
            self.settings_to_cmd_args_env(
                {
                    "NAME": "settingdbname",
                    "USER": "settinguser",
                    "PASSWORD": "settingpassword",
                    "HOST": "settinghost",
                    "PORT": settings_port,
                    "OPTIONS": {"port": options_port},
                }
            ),
            (expected_args, expected_env),
        )

    def test_sigint_handler(self):
        """
        SIGINT is ignored in Python and passed to MongoDB to abort queries.
        """

        def _mock_subprocess_run(*args, **kwargs):  # noqa: ARG001
            handler = signal.getsignal(signal.SIGINT)
            self.assertEqual(handler, signal.SIG_IGN)

        sigint_handler = signal.getsignal(signal.SIGINT)
        # The default handler isn't SIG_IGN.
        self.assertNotEqual(sigint_handler, signal.SIG_IGN)
        with mock.patch("subprocess.run", new=_mock_subprocess_run):
            connection.client.runshell([])
        # dbshell restores the original handler.
        self.assertEqual(sigint_handler, signal.getsignal(signal.SIGINT))
