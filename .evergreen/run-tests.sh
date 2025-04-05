#!/usr/bin/bash

set -eux

# Install django-mongodb-backend
/opt/python/3.12/bin/python3 -m venv venv
. venv/bin/activate
python -m pip install -U pip
pip install -e .

# Install django and test dependencies
git clone --branch mongodb-6.0.x https://github.com/mongodb-forks/django django_repo
pushd django_repo/tests/
pip install -e ..
pip install -r requirements/py3.txt
popd

# Copy the test settings files
cp ./.github/workflows/*_settings.py django_repo/tests/

# Copy the test runner file
cp ./.github/workflows/runtests.py django_repo/tests/runtests_.py

# Run tests
python django_repo/tests/runtests_.py
