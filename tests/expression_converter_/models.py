from django.db import models


class NullableJSONModel(models.Model):
    value = models.JSONField(blank=True, null=True)

    class Meta:
        required_db_features = {"supports_json_field"}


class Tag(models.Model):
    name = models.CharField(max_length=10)

    def __str__(self):
        return self.name
