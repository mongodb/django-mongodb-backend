from django.db import migrations, models

import django_mongodb_backend


class Migration(migrations.Migration):
    dependencies = []

    operations = [
        migrations.CreateModel(
            name="IntegerArrayDefaultModel",
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
                    "field",
                    django_mongodb_backend.fields.ArrayField(models.IntegerField()),
                ),
            ],
            options={},
            bases=(models.Model,),
        ),
    ]
