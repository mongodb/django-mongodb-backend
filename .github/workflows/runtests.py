#!/usr/bin/env python
import os
import pathlib
import sys

test_apps = [
    "gis_tests",
]
runtests = pathlib.Path(__file__).parent.resolve() / "runtests.py"
run_tests_cmd = f"python3 {runtests} %s --settings mongodb_settings -v 2"

shouldFail = False
for app_name in test_apps:
    res = os.system(run_tests_cmd % app_name)  # noqa: S605
    if res != 0:
        shouldFail = True
sys.exit(1 if shouldFail else 0)
