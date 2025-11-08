#!/usr/bin/env python
import os
import pathlib
import sys

from django.core.exceptions import ImproperlyConfigured

test_apps = [
    # Add directories in django_mongodb_backend/tests
    *sorted(
        [
            x.name
            for x in (pathlib.Path(__file__).parent.parent.parent.resolve() / "tests").iterdir()
            # Omit GIS tests unless GIS libraries are installed.
            if x.name != "gis_tests_"
        ]
    ),
]

try:
    from django.contrib.gis.db import models  # noqa: F401
except ImproperlyConfigured:
    # GIS libraries (GDAL/GEOS) not installed.
    pass
else:
    test_apps.extend(["gis_tests", "gis_tests_"])

runtests = pathlib.Path(__file__).parent.resolve() / "runtests.py"
run_tests_cmd = f"python3 {runtests} %s --settings %s -v 2"

shouldFail = False
for app_name in test_apps:
    # Use the custom settings module only for django_mongodb_backend's tests
    # (which always end with an underscore). Some of Django's tests aren't
    # compatible with extra DATABASE_ROUTERS or other DATABASES aliases.
    settings_module = (
        os.environ.get("DJANGO_SETTINGS_MODULE", "mongodb_settings")
        if app_name.endswith("_")
        else "django_settings"
    )
    res = os.system(run_tests_cmd % (app_name, settings_module))  # noqa: S605
    if res != 0:
        shouldFail = True
sys.exit(1 if shouldFail else 0)
