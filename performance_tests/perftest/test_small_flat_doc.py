from pathlib import Path
from unittest import TestCase

from bson import encode, json_util

from .base import PerformanceTest
from .models import (
    ForeignKeyModel,
    SmallFlatModel,
    SmallFlatModelFk,
)


class SmallFlatDocTest(PerformanceTest):
    """Parent class for small flat document tests."""

    dataset = "small_doc.json"

    def setUp(self):
        super().setUp()
        with open(  # noqa: PTH123
            Path(self.test_data_path) / Path("flat-models") / self.dataset
        ) as data:
            self.document = json_util.loads(data.read())
        self.setUpData()
        self.data_size = len(encode(self.document)) * self.num_docs

    def setUpData(self):
        SmallFlatModel.objects.bulk_create(
            SmallFlatModel(**self.document) for _ in range(self.num_docs)
        )


class TestSmallFlatDocCreation(SmallFlatDocTest, TestCase):
    """Benchmark for creating a small flat document."""

    def setUpData(self):
        # Don't create data since this is the creation benchmark.
        pass

    def do_task(self):
        for _ in range(self.num_docs):
            SmallFlatModel.objects.create(**self.document)

    def after(self):
        SmallFlatModel.objects.all().delete()


class TestSmallFlatDocUpdate(SmallFlatDocTest, TestCase):
    """Benchmark for updating a field within a small flat document."""

    def setUp(self):
        super().setUp()
        self.models = list(SmallFlatModel.objects.all())
        self.data_size = len(encode({"field1": "updated_value0"})) * self.num_docs
        self.iteration = 0

    def do_task(self):
        for model in self.models:
            model.field1 = "updated_value" + str(self.iteration)
            model.save()
        self.iteration += 1

    def tearDown(self):
        super().tearDown()
        SmallFlatModel.objects.all().delete()


class TestSmallFlatDocFilterById(SmallFlatDocTest, TestCase):
    """Benchmark for filtering small flat documents by their primary key."""

    def setUp(self):
        super().setUp()
        self.ids = SmallFlatModel.objects.values_list("id", flat=True)

    def do_task(self):
        for _id in self.ids:
            list(SmallFlatModel.objects.filter(id=_id))

    def tearDown(self):
        super().tearDown()
        SmallFlatModel.objects.all().delete()


class TestSmallFlatDocFilterByForeignKey(SmallFlatDocTest, TestCase):
    """Benchmark for filtering small flat documents by a foreign key field."""

    def setUp(self):
        super().setUp()
        self.fks = []
        for _ in range(self.num_docs):
            model = SmallFlatModelFk(**self.document)
            foreign_key_model = ForeignKeyModel.objects.create(name="foreign_key_name")
            self.fks.append(foreign_key_model)
            foreign_key_model.save()
            model.field_fk = foreign_key_model
            model.save()

    def setUpData(self):
        # Don't create data since foreign keys will be added.
        pass

    def do_task(self):
        for fk in self.fks:
            list(SmallFlatModelFk.objects.filter(field_fk__id=fk.id))

    def tearDown(self):
        super().tearDown()
        SmallFlatModelFk.objects.all().delete()
        ForeignKeyModel.objects.all().delete()


class TestSmallFlatDocFilterPkByIn(SmallFlatDocTest, TestCase):
    """Benchmark for filtering small flat documents using the __in operator for primary keys."""

    def setUp(self):
        super().setUp()
        self.ids = SmallFlatModel.objects.values_list("id", flat=True)

    def do_task(self):
        list(SmallFlatModel.objects.filter(id__in=self.ids))

    def tearDown(self):
        super().tearDown()
        SmallFlatModel.objects.all().delete()
