#!/usr/bin/bash

set -eux

export OUTPUT_FILE="results.json"

# Install django-mongodb-backend
/opt/python/3.12/bin/python3 -m venv venv
. venv/bin/activate
python -m pip install -U pip
pip install -e .

python .evergreen/perf/runtests.py
mv performance_tests/$OUTPUT_FILE $OUTPUT_FILE
mv performance_tests/report.json report.json
