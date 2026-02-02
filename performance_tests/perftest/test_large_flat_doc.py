from pathlib import Path
from unittest import TestCase

from bson import encode, json_util

from .base import PerformanceTest
from .models import LargeFlatModel


class LargeFlatDocTest(PerformanceTest):
    """Parent class for large flat document tests."""

    dataset = "large_doc.json"

    def setUp(self):
        super().setUp()
        with open(  # noqa: PTH123
            Path(self.test_data_path) / Path("flat-models") / self.dataset
        ) as data:
            self.document = json_util.loads(data.read())

        self.data_size = len(encode(self.document)) * self.num_docs
        self.documents = [self.document.copy() for _ in range(self.num_docs)]


class TestLargeFlatDocCreation(LargeFlatDocTest, TestCase):
    """Benchmark for creating a large flat document."""

    def do_task(self):
        for doc in self.documents:
            LargeFlatModel.objects.create(**doc)

    def after(self):
        LargeFlatModel.objects.all().delete()


class TestLargeFlatDocUpdate(LargeFlatDocTest, TestCase):
    """Benchmark for updating a field within a large flat document."""

    def setUp(self):
        super().setUp()
        for doc in self.documents:
            LargeFlatModel.objects.create(**doc)
        self.models = list(LargeFlatModel.objects.all())
        self.data_size = len(encode({"field1": "updated_value0"})) * self.num_docs
        self.iteration = 0

    def do_task(self):
        for model in self.models:
            model.field1 = "updated_value" + str(self.iteration)
            model.save()
        self.iteration += 1

    def tearDown(self):
        super().tearDown()
        LargeFlatModel.objects.all().delete()


class TestLargeFlatDocFilterPkByIn(LargeFlatDocTest, TestCase):
    """Benchmark for filtering large flat documents using the __in operator for primary keys."""

    def setUp(self):
        super().setUp()
        models = []
        for doc in self.documents:
            models.append(LargeFlatModel(**doc))
        LargeFlatModel.objects.bulk_create(models)
        self.ids = [model.id for model in models]

    def do_task(self):
        list(LargeFlatModel.objects.filter(id__in=self.ids))

    def tearDown(self):
        super().tearDown()
        LargeFlatModel.objects.all().delete()
