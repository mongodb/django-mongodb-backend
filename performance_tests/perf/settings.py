# Django settings for the performance tests.
DATABASES = {
    "default": {
        "ENGINE": "django_mongodb_backend",
        "NAME": "benchmarking",
    },
}

SECRET_KEY = "django_tests_secret_key"  # noqa: S105

INSTALLED_APPS = ["perf"]

DEFAULT_AUTO_FIELD = "django_mongodb_backend.fields.ObjectIdAutoField"

TEST_RUNNER = "perf.runner.TestRunner"
