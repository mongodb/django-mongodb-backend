from django.db import models

from django_mongodb_backend.fields import EmbeddedModelArrayField, EmbeddedModelField
from django_mongodb_backend.models import EmbeddedModel


class SmallFlatModel(models.Model):
    field1 = models.CharField(max_length=100)
    field2 = models.CharField(max_length=100)
    field3 = models.CharField(max_length=100)
    field4 = models.CharField(max_length=100)
    field5 = models.CharField(max_length=100)
    field6 = models.CharField(max_length=100)
    field7 = models.CharField(max_length=100)
    field8 = models.IntegerField()
    field9 = models.IntegerField()
    field10 = models.IntegerField()
    field11 = models.IntegerField()
    field12 = models.IntegerField()
    field13 = models.IntegerField()

    class Meta:
        indexes = [
            models.Index(fields=["field1"], name="field1_idx"),
        ]


class ForeignKeyModel(models.Model):
    name = models.CharField(max_length=100)


class SmallFlatModelFk(models.Model):
    field1 = models.CharField(max_length=100)
    field2 = models.CharField(max_length=100)
    field3 = models.CharField(max_length=100)
    field4 = models.CharField(max_length=100)
    field5 = models.CharField(max_length=100)
    field6 = models.CharField(max_length=100)
    field7 = models.CharField(max_length=100)
    field8 = models.IntegerField()
    field9 = models.IntegerField()
    field10 = models.IntegerField()
    field11 = models.IntegerField()
    field12 = models.IntegerField()
    field13 = models.IntegerField()
    field_fk = models.ForeignKey(ForeignKeyModel, on_delete=models.DO_NOTHING)


# Construct LargeFlatModel programmatically to avoid a very long model
# definition.
large_flat_model_attrs = {
    "__module__": "perf.models",
    "image_field": models.BinaryField(),
}
for i in range(125):
    large_flat_model_attrs[f"field{i + 1}"] = models.CharField(max_length=100)
    large_flat_model_attrs[f"field{i + 126}"] = models.IntegerField()

LargeFlatModel = type("LargeFlatModel", (models.Model,), large_flat_model_attrs)


class StringEmbeddedModel(EmbeddedModel):
    unique_field = models.CharField(max_length=100)
    field1 = models.CharField(max_length=100)
    field2 = models.CharField(max_length=100)
    field3 = models.CharField(max_length=100)
    field4 = models.CharField(max_length=100)
    field5 = models.CharField(max_length=100)
    field6 = models.CharField(max_length=100)
    field7 = models.CharField(max_length=100)
    field8 = models.CharField(max_length=100)
    field9 = models.CharField(max_length=100)
    field10 = models.CharField(max_length=100)
    field11 = models.CharField(max_length=100)
    field12 = models.CharField(max_length=100)
    field13 = models.CharField(max_length=100)
    field14 = models.CharField(max_length=100)
    field15 = models.CharField(max_length=100)


class IntegerEmbeddedModel(EmbeddedModel):
    field1 = models.IntegerField()
    field2 = models.IntegerField()
    field3 = models.IntegerField()
    field4 = models.IntegerField()
    field5 = models.IntegerField()
    field6 = models.IntegerField()
    field7 = models.IntegerField()
    field8 = models.IntegerField()
    field9 = models.IntegerField()
    field10 = models.IntegerField()
    field11 = models.IntegerField()
    field12 = models.IntegerField()
    field13 = models.IntegerField()
    field14 = models.IntegerField()
    field15 = models.IntegerField()


class LargeNestedModel(models.Model):
    embedded_str_doc_1 = EmbeddedModelField(StringEmbeddedModel)
    embedded_str_doc_2 = EmbeddedModelField(StringEmbeddedModel)
    embedded_str_doc_3 = EmbeddedModelField(StringEmbeddedModel)
    embedded_str_doc_4 = EmbeddedModelField(StringEmbeddedModel)
    embedded_str_doc_5 = EmbeddedModelField(StringEmbeddedModel)
    embedded_str_doc_array = EmbeddedModelArrayField(StringEmbeddedModel)
    embedded_int_doc_8 = EmbeddedModelField(IntegerEmbeddedModel)
    embedded_int_doc_9 = EmbeddedModelField(IntegerEmbeddedModel)
    embedded_int_doc_10 = EmbeddedModelField(IntegerEmbeddedModel)
    embedded_int_doc_11 = EmbeddedModelField(IntegerEmbeddedModel)
    embedded_int_doc_12 = EmbeddedModelField(IntegerEmbeddedModel)
    embedded_int_doc_13 = EmbeddedModelField(IntegerEmbeddedModel)
    embedded_int_doc_14 = EmbeddedModelField(IntegerEmbeddedModel)
