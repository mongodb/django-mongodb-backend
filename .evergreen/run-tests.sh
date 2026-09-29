#!/usr/bin/bash

set -eux

# Export secrets as environment variables
# https://github.com/mongodb-labs/drivers-evergreen-tools/blob/master/.evergreen/csfle/README.md#usage
if [[ "${1:-}" == "encryption" ]]; then
    . ../secrets-export.sh
fi

# Set up virtual environment
/opt/python/3.12/bin/python3 -m venv venv
. venv/bin/activate
python -m pip install -U pip

# Install django-mongodb-backend
if [[ "${1:-}" == "encryption" ]]; then
    # Install encryption dependencies for the Queryable Encryption build
    pip install -e '.[encryption]'
else
    pip install -e .
fi

# Install django and test dependencies
git clone --branch mongodb-6.1.x https://github.com/mongodb-forks/django django_repo
pushd django_repo/tests/
pip install -e ..
pip install -r requirements/py3.txt
# Required to report test XML results.
pip install unittest-xml-reporting
popd

# Copy the test settings files
cp ./.github/workflows/*_settings.py django_repo/tests/

# Copy the XML test runner
cp ./.evergreen/xml_test_runner.py django_repo/tests/

export EVERGREEN_TEST_RESULTS=1

# Copy the test runner file
cp ./.github/workflows/runtests.py django_repo/tests/runtests_.py

# Run tests
python django_repo/tests/runtests_.py
