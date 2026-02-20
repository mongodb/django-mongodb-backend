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
        self.setUpData()
        self.data_size = len(encode(self.document)) * self.num_docs

    def setUpData(self):
        LargeFlatModel.objects.bulk_create(
            LargeFlatModel(**self.document) for _ in range(self.num_docs)
        )

    def tearDown(self):
        super().tearDown()
        LargeFlatModel.objects.all().delete()


class TestLargeFlatDocCreation(LargeFlatDocTest, TestCase):
    """Creating a large flat document."""

    def setUpData(self):
        # Don't create data since this is the creation benchmark.
        pass

    def do_task(self):
        for _ in range(self.num_docs):
            LargeFlatModel.objects.create(**self.document)

    def after(self):
        LargeFlatModel.objects.all().delete()


class TestLargeFlatDocUpdate(LargeFlatDocTest, TestCase):
    """Updating a field within a large flat document."""

    def setUp(self):
        super().setUp()
        self.models = list(LargeFlatModel.objects.all())
        self.data_size = len(encode({"field1": "updated_value0"})) * self.num_docs
        self.iteration = 0

    def do_task(self):
        for model in self.models:
            model.field1 = "updated_value" + str(self.iteration)
            model.save()
        self.iteration += 1


class TestLargeFlatDocFilterPkByIn(LargeFlatDocTest, TestCase):
    """Filtering large flat documents using __in for primary keys."""

    def setUp(self):
        super().setUp()
        self.ids = LargeFlatModel.objects.values_list("id", flat=True)[:100]

    def do_task(self):
        list(LargeFlatModel.objects.filter(id__in=self.ids))
