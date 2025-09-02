# Django MongoDB Backend

## Index
* [Documentation](https://www.mongodb.com/docs/languages/python/django-mongodb/current/)
* [Getting Started](https://www.mongodb.com/docs/languages/python/django-mongodb/current/get-started/)
* [Model Your Data](https://www.mongodb.com/docs/languages/python/django-mongodb/current/model-data/)
* [Limitations & Future Work](https://www.mongodb.com/docs/languages/python/django-mongodb/current/limitations-upcoming/)

The documentation in the "docs" directory is online at
https://django-mongodb-backend.readthedocs.io/en/latest/.

## Install

Use the version of `django-mongodb-backend` that corresponds to your version of
Django. For example, to get the latest compatible release for Django 5.2.x:
```bash
pip install django-mongodb-backend==5.2.*
```

## Quickstart

### Start project

From your shell, run the following command to create a new Django project
called `example` using our custom template. Make sure the zipfile referenced
at the end of the template link corresponds to your version of Django.

You can check what version of Django you're using with:
```bash
django-admin --version
```

The snippet below specifies `5.2.x.zip` at the end of
the template url to get the template for any Django version matching 5.2:

```bash
django-admin startproject example --template https://github.com/mongodb-labs/django-mongodb-project/archive/refs/heads/5.2.x.zip
```


### Connect to the database

Navigate to your `example/settings.py` file and replace the `DATABASES`
setting like so:

```python
DATABASES = {
    "default": django_mongodb_backend.parse_uri(
        "<CONNECTION_STRING_URI>", db_name="example"
    ),
}
```

### Run the server
To verify that you installed Django MongoDB Backend and correctly configured your project, run the following command from your project root:
```bash
python manage.py runserver
```
Then, visit http://127.0.0.1:8000/. This page displays a "Congratulations!" message and an image of a rocket.


## Capabilities of Django MongoDB Backend

- **Model MongoDB Documents Through Django’s ORM**

  - Store Django model instances as MongoDB documents.
  - Maps Django's built-in fields to MongoDB data types.
  - Provides custom fields for arrays (`ArrayField`) and embedded documents (`EmbeddedModelField`).
  - Supports core migration functionalities.
- **Index Management**
  - Create single, compound, partial, and unique indexes using Django Indexes.
- **Querying Data**
  - Supports most of the Django QuerySet API.
  - Supports relational field usage and executes `JOIN` operations with MQL.
  - A custom `QuerySet.raw_aggregate` method exposes MongoDB-specific operations like Vector Search, Atlas Search, and GeoSpatial querying to yield Django QuerySet results.
- **Administrator Dashboard & Authentication**
  - Manage your data in Django’s admin site.
  - Fully integrated with Django's authentication framework.
  - Supports native user management features like creating users and session management.


### Issues & Help

We're glad to have such a vibrant community of users of Django MongoDB Backend.
You can ask questions and request features through the
[MongoDB Community Forums](https://www.mongodb.com/community/forums/tag/python).


#### Bugs / Feature Requests
To report a bug or to request a new feature in Django MongoDB Backend, please open an issue in JIRA, our issue-management tool, using the following steps:

1. [Create a JIRA account.](https://jira.mongodb.org/)

2. Navigate to the [Python Integrations project](https://jira.mongodb.org/projects/INTPYTHON/).

3. Click **Create Issue**. Please provide as much information as possible about the issue and the steps to reproduce it.

Bug reports in JIRA for the Django MongoDB Backend project can be viewed by everyone.

If you identify a security vulnerability in the driver or in any other MongoDB project, please report it according to the instructions found in [Create a Vulnerability Report](https://www.mongodb.com/docs/manual/tutorial/create-a-vulnerability-report/).
