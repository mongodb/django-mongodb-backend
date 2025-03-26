from django.db import migrations, models

import django_mongodb_backend


class Migration(migrations.Migration):
    dependencies = []

    operations = [
        migrations.CreateModel(
            name="CharTextArrayIndexModel",
            fields=[
                (
                    "id",
                    django_mongodb_backend.fields.ObjectIdAutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                (
                    "char",
                    django_mongodb_backend.fields.ArrayField(
                        models.CharField(max_length=10), db_index=True, max_size=100
                    ),
                ),
                ("char2", models.CharField(max_length=11, db_index=True)),
                (
                    "text",
                    django_mongodb_backend.fields.ArrayField(models.TextField(), db_index=True),
                ),
            ],
            options={},
            bases=(models.Model,),
        ),
    ]
