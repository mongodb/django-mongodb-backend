from django.db import migrations, models

import django_mongodb_backend


class Migration(migrations.Migration):
    dependencies = [
        ("model_fields_", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="integerarraydefaultmodel",
            name="field_2",
            field=django_mongodb_backend.fields.ArrayField(models.IntegerField(), default=[]),
            preserve_default=False,
        ),
    ]
