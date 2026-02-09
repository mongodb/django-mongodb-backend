from pathlib import Path
from unittest import TestCase

from bson import ObjectId, encode, json_util

from .base import PerformanceTest
from .models import (
    IntegerEmbeddedModel,
    LargeNestedModel,
    StringEmbeddedModel,
)


class LargeNestedDocTest(PerformanceTest):
    """Parent class for large nested document tests."""

    dataset = "large_doc_nested.json"

    def setUp(self):
        super().setUp()
        with open(  # noqa: PTH123
            Path(self.test_data_path) / Path("nested-models") / self.dataset
        ) as data:
            self.document = json_util.loads(data.read())
        self.setUpData()
        self.data_size = len(encode(self.document)) * self.num_docs

    def setUpData(self):
        for _ in range(self.num_docs):
            model = LargeNestedModel()
            for field_name, model_data in self.document.items():
                if "array" in field_name:
                    array_models = []
                    for item in model_data:
                        embedded_str_model = StringEmbeddedModel(**item)
                        embedded_str_model.unique_field = str(ObjectId())
                        array_models.append(embedded_str_model)
                    setattr(model, field_name, array_models)
                elif "embedded_str_doc" in field_name:
                    embedded_str_model = StringEmbeddedModel(**model_data)
                    embedded_str_model.unique_field = str(ObjectId())
                    setattr(model, field_name, embedded_str_model)
                else:
                    embedded_int_model = IntegerEmbeddedModel(**model_data)
                    setattr(model, field_name, embedded_int_model)
            model.save()


class TestLargeNestedDocCreation(LargeNestedDocTest, TestCase):
    """Benchmark for creating a large nested document."""

    def setUpData(self):
        # Don't create data since this is the creation benchmark.
        pass

    def do_task(self):
        for _ in range(self.num_docs):
            model = LargeNestedModel()
            for field_name, model_data in self.document.items():
                if "array" in field_name:
                    array_models = []
                    for item in model_data:
                        embedded_str_model = StringEmbeddedModel(**item)
                        embedded_str_model.unique_field = str(ObjectId())
                        array_models.append(embedded_str_model)
                    setattr(model, field_name, array_models)
                elif "embedded_str_doc" in field_name:
                    embedded_str_model = StringEmbeddedModel(**model_data)
                    embedded_str_model.unique_field = str(ObjectId())
                    setattr(model, field_name, embedded_str_model)
                else:
                    embedded_int_model = IntegerEmbeddedModel(**model_data)
                    setattr(model, field_name, embedded_int_model)
            model.save()

    def after(self):
        LargeNestedModel.objects.all().delete()


class TestLargeNestedDocUpdate(LargeNestedDocTest, TestCase):
    """Benchmark for updating an embedded field within a large nested document."""

    def setUp(self):
        super().setUp()
        self.models = list(LargeNestedModel.objects.all())
        self.data_size = len(encode({"field1": "updated_value0"})) * self.num_docs
        self.iteration = 0

    def do_task(self):
        for model in self.models:
            model.embedded_str_doc_1.field1 = "updated_value" + str(self.iteration)
            model.save()
        self.iteration += 1

    def tearDown(self):
        super().tearDown()
        LargeNestedModel.objects.all().delete()


class TestLargeNestedDocFilterById(LargeNestedDocTest, TestCase):
    """Benchmark for filtering large nested documents by a unique field in an embedded document."""

    def setUp(self):
        super().setUp()
        self.setUpData()
        self.ids = [
            model.embedded_str_doc_1.unique_field for model in list(LargeNestedModel.objects.all())
        ]

    def do_task(self):
        for _id in self.ids:
            list(LargeNestedModel.objects.filter(embedded_str_doc_1__unique_field=_id))

    def tearDown(self):
        super().tearDown()
        LargeNestedModel.objects.all().delete()


class TestLargeNestedDocFilterArray(LargeNestedDocTest, TestCase):
    """Benchmark for filtering large nested documents using the __in operator
    for unique values in an embedded document array."""

    def setUp(self):
        super().setUp()
        self.ids = [
            model.embedded_str_doc_array[0].unique_field
            for model in list(LargeNestedModel.objects.all())
        ]

    def do_task(self):
        for _id in self.ids:
            list(LargeNestedModel.objects.filter(embedded_str_doc_array__unique_field__in=[_id]))

    def tearDown(self):
        super().tearDown()
        LargeNestedModel.objects.all().delete()
