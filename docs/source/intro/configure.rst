===================================================
Configuring a project to use Django MongoDB Backend
===================================================

Aftering :doc:`installing Django MongoDB Backend <install>`, you must take some
additional steps to configure your project.

.. _specifying the-default-pk-field:

Specifying the default primary key field
========================================

In your Django settings, you must specify that all models should use
:class:`~django_mongodb_backend.fields.ObjectIdAutoField`.

You can create a new project that's configured based on these steps using a
project template:

.. code-block:: bash

    $ django-admin startproject mysite --template https://github.com/mongodb-labs/django-mongodb-project/archive/refs/heads/5.2.x.zip

(If you're using a version of Django other than 5.2.x, replace the two numbers
to match the first two numbers from your version.)

This template includes the following line in ``settings.py``::

    DEFAULT_AUTO_FIELD = "django_mongodb_backend.fields.ObjectIdAutoField"

But this setting won't override any apps that have an ``AppConfig`` that
specifies :attr:`~django.apps.AppConfig.default_auto_field`. For those apps,
you'll need to create a custom :class:`~django.apps.AppConfig`.

For example, the project template includes ``<project_name>/apps.py``::

    from django.contrib.admin.apps import AdminConfig
    from django.contrib.auth.apps import AuthConfig
    from django.contrib.contenttypes.apps import ContentTypesConfig


    class MongoAdminConfig(AdminConfig):
        default_auto_field = "django_mongodb_backend.fields.ObjectIdAutoField"


    class MongoAuthConfig(AuthConfig):
        default_auto_field = "django_mongodb_backend.fields.ObjectIdAutoField"


    class MongoContentTypesConfig(ContentTypesConfig):
        default_auto_field = "django_mongodb_backend.fields.ObjectIdAutoField"

Each app reference in the :setting:`INSTALLED_APPS` setting must point to the
corresponding ``AppConfig``. For example, instead of ``'django.contrib.admin'``,
the template uses ``'<project_name>.apps.MongoAdminConfig'``.

Configuring migrations
======================

Because all models must use
:class:`~django_mongodb_backend.fields.ObjectIdAutoField`, each third-party
and contrib app you use needs to have its own migrations specific to MongoDB.

For example, ``settings.py`` in the project template specifies::

    MIGRATION_MODULES = {
        "admin": "mongo_migrations.admin",
        "auth": "mongo_migrations.auth",
        "contenttypes": "mongo_migrations.contenttypes",
    }

The project template includes these migrations, but you can generate them if
you're setting things up manually or if you need to create migrations for
third-party apps. For example:

.. code-block:: bash

    $ python manage.py makemigrations admin auth contenttypes
    Migrations for 'admin':
      mongo_migrations/admin/0001_initial.py
        - Create model LogEntry
    ...

Creating Django applications
============================

Whenever you run ``python manage.py startapp``, you must remove the line::

    default_auto_field = 'django.db.models.BigAutoField'

from the new application's ``apps.py`` file (or change it to reference
``"django_mongodb_backend.fields.ObjectIdAutoField"``).

Alternatively, you can use the following :djadmin:`startapp` template which
includes this change:

.. code-block:: bash

    $ python manage.py startapp myapp --template https://github.com/mongodb-labs/django-mongodb-app/archive/refs/heads/5.2.x.zip

(If you're using a version of Django other than 5.2.x, replace the two numbers
to match the first two numbers from your version.)

.. _configuring-databases-setting:

Configuring the ``DATABASES`` setting
=====================================

After you've set up a project, configure Django's :setting:`DATABASES` setting
similar to this::

    DATABASES = {
        "default": {
            "ENGINE": "django_mongodb_backend",
            "HOST": "mongodb+srv://cluster0.example.mongodb.net",
            "NAME": "my_database",
            "USER": "my_user",
            "PASSWORD": "my_password",
            "PORT": 27017,
            "OPTIONS": {
                # Example:
                "retryWrites": "true",
                "w": "majority",
                "tls": "false",
            },
        },
    }

For a localhost configuration, you can omit :setting:`HOST` or specify
``"HOST": "localhost"``.

:setting:`HOST` only needs a scheme prefix for SRV connections
(``mongodb+srv://``). A ``mongodb://`` prefix is never required.

:setting:`OPTIONS` is an optional dictionary of parameters that will be passed
to :class:`~pymongo.mongo_client.MongoClient`.

Specify :setting:`USER` and :setting:`PASSWORD` if your database requires
authentication.

:setting:`PORT` is optional if unchanged from MongoDB's default of 27017.

For a replica set or sharded cluster where you have multiple hosts, include
all of them in :setting:`HOST`, e.g.
``"mongodb://mongos0.example.com:27017,mongos1.example.com:27017"``.

Alternatively, if you prefer to simply paste in a MongoDB URI rather than parse
it into the format above, you can use
:func:`~django_mongodb_backend.utils.parse_uri`::

    import django_mongodb_backend

    MONGODB_URI = "mongodb+srv://my_user:my_password@cluster0.example.mongodb.net/myDatabase?retryWrites=true&w=majority&tls=false"
    DATABASES["default"] = django_mongodb_backend.parse_uri(MONGODB_URI)

This constructs a :setting:`DATABASES` setting equivalent to the first example.

.. _configuring-database-routers-setting:

Configuring the ``DATABASE_ROUTERS`` setting
============================================

If you intend to use :doc:`embedded models </topics/embedded-models>`, you must
configure the :setting:`DATABASE_ROUTERS` setting so that a collection for
these models isn't created and so that embedded models won't be treated as
normal models by :djadmin:`dumpdata`::

    DATABASE_ROUTERS = ["django_mongodb_backend.routers.MongoRouter"]

(If you've used the :djadmin:`startproject` template, this line is already
present.)

Congratulations, your project is ready to go!

.. seealso::

    :doc:`/howto/contrib-apps`
