# Django MongoDB Backend

## Documentation

Documentation written in the style of MongoDB's documentation is available at
https://www.mongodb.com/docs/languages/python/django-mongodb/current/.

Documentation written in the style of Django's documentation is available at
https://django-mongodb-backend.readthedocs.io/en/latest/.

## Quick Start

### Install

Use the version of `django-mongodb-backend` that corresponds to your version of
Django. For example, to get the latest compatible release for Django 5.2.x:

```bash
pip install django-mongodb-backend==5.2.*
```

### Create a project

From your shell, run the following command to create a new Django project
called `example` using our project template. Make sure the end of the template
URL corresponds to your version of Django (e.g. `5.2.x.zip` for any Django
5.2.x version).

```bash
django-admin startproject example --template https://github.com/mongodb-labs/django-mongodb-project/archive/refs/heads/5.2.x.zip
```

You can check what version of Django you're using with:

```bash
django-admin --version
```

### Connect to the database

Navigate to your `example/settings.py` file and replace the `DATABASES`
setting like so:

```python
DATABASES = {
    "default": {
        "ENGINE": "django_mongodb_backend",
        "HOST": "<CONNECTION_STRING_URI>",
        "NAME": "db_name",
    },
}
```

### Run the server

To verify that you correctly configured your project, run the following command
from your project root:

```bash
python manage.py runserver
```

Then, visit http://127.0.0.1:8000/. This page displays a "Congratulations!"
message and an image of a rocket.

## Getting Help

You can ask usage questions on the [MongoDB Community Forums](https://www.mongodb.com/community/forums/tag/python).

## Reporting Bugs and Requesting Features

To report a bug or request a new feature in Django MongoDB Backend, please open
an issue in JIRA:

1. [Create a JIRA account.](https://jira.mongodb.org/)
2. Navigate to the [Python Integrations project](https://jira.mongodb.org/projects/INTPYTHON/).
3. Click **Create Issue**. Please provide as much information as possible about
the issue and the steps to reproduce it.

Bug reports for the Django MongoDB Backend project can be viewed by everyone.

If you identify a security vulnerability in this project or in any other
MongoDB project, please report it according to the instructions found at
[Create a Vulnerability Report](https://www.mongodb.com/docs/manual/tutorial/create-a-vulnerability-report/).
