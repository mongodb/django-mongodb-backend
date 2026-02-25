#!/usr/bin/env python
import os
import sys

import django
from django.core.management import call_command

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "perf.settings")


if __name__ == "__main__":
    django.setup()
    call_command("test", sys.argv[1:])
