#!/usr/bin/env python
import os
import sys

import django
from django.conf import settings
from django.test.utils import get_runner
from perftest.base import write_output_file

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "perftest.settings")


if __name__ == "__main__":
    django.setup()
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    failures = test_runner.run_tests(["perftest"])
    write_output_file()
    sys.exit(bool(failures))
