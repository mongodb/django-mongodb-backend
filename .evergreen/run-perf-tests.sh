#!/usr/bin/bash

set -eux

export OUTPUT_FILE="results.json"

# Install django-mongodb-backend
/opt/python/3.10/bin/python3 -m venv venv
. venv/bin/activate
python -m pip install -U pip
pip install -e .

python .evergreen/run_perf_test.py
mv tests/performance/$OUTPUT_FILE $OUTPUT_FILE
mv tests/performance/report.json report.json
