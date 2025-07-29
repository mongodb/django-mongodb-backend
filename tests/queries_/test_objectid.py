from bson import ObjectId
from django.core.exceptions import ValidationError
from django.test import TestCase

from .models import Order, OrderItem, Tag


class ObjectIdTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.group_id_str_1 = "1" * 24
        cls.group_id_obj_1 = ObjectId(cls.group_id_str_1)
        cls.group_id_str_2 = "2" * 24
        cls.group_id_obj_2 = ObjectId(cls.group_id_str_2)

        cls.t1 = Tag.objects.create(name="t1")
        cls.t2 = Tag.objects.create(name="t2", parent=cls.t1)
        cls.t3 = Tag.objects.create(name="t3", parent=cls.t1, group_id=cls.group_id_str_1)
        cls.t4 = Tag.objects.create(name="t4", parent=cls.t3, group_id=cls.group_id_obj_2)
        cls.t5 = Tag.objects.create(name="t5", parent=cls.t3)

    def test_filter_group_id_is_null_false(self):
        """Filter objects where group_id is not null."""
        qs = Tag.objects.filter(group_id__isnull=False).order_by("name")
        self.assertSequenceEqual(qs, [self.t3, self.t4])

    def test_filter_group_id_is_null_true(self):
        """Filter objects where group_id is null."""
        qs = Tag.objects.filter(group_id__isnull=True).order_by("name")
        self.assertSequenceEqual(qs, [self.t1, self.t2, self.t5])

    def test_filter_group_id_equal_str(self):
        """Filter by group_id with a specific string value."""
        qs = Tag.objects.filter(group_id=self.group_id_str_1).order_by("name")
        self.assertSequenceEqual(qs, [self.t3])

    def test_filter_group_id_equal_obj(self):
        """Filter by group_id with a specific ObjectId value."""
        qs = Tag.objects.filter(group_id=self.group_id_obj_1).order_by("name")
        self.assertSequenceEqual(qs, [self.t3])

    def test_filter_group_id_in_str_values(self):
        """Filter by group_id with string values in a list."""
        ids = [self.group_id_str_1, self.group_id_str_2]
        qs = Tag.objects.filter(group_id__in=ids).order_by("name")
        self.assertSequenceEqual(qs, [self.t3, self.t4])

    def test_filter_group_id_in_obj_values(self):
        """Filter by group_id with ObjectId values in a list."""
        ids = [self.group_id_obj_1, self.group_id_obj_2]
        qs = Tag.objects.filter(group_id__in=ids).order_by("name")
        self.assertSequenceEqual(qs, [self.t3, self.t4])

    def test_filter_group_id_equal_subquery(self):
        """Filter by group_id using a subquery."""
        subquery = Tag.objects.filter(name="t3").values("group_id")
        qs = Tag.objects.filter(group_id__in=subquery).order_by("name")
        self.assertSequenceEqual(qs, [self.t3])

    def test_filter_group_id_in_subquery(self):
        """Filter by group_id using a subquery with multiple values."""
        subquery = Tag.objects.filter(name__in=["t3", "t4"]).values("group_id")
        qs = Tag.objects.filter(group_id__in=subquery).order_by("name")
        self.assertSequenceEqual(qs, [self.t3, self.t4])

    def test_filter_parent_by_children_values_str(self):
        """Query to select parents of children with specific string group_id."""
        child_ids = Tag.objects.filter(group_id=self.group_id_str_1).values_list("id", flat=True)
        parent_qs = Tag.objects.filter(children__id__in=child_ids).distinct().order_by("name")
        self.assertSequenceEqual(parent_qs, [self.t1])

    def test_filter_parent_by_children_values_obj(self):
        """Query to select parents of children with specific ObjectId group_id."""
        child_ids = Tag.objects.filter(group_id=self.group_id_obj_1).values_list("id", flat=True)
        parent_qs = Tag.objects.filter(children__id__in=child_ids).distinct().order_by("name")
        self.assertSequenceEqual(parent_qs, [self.t1])

    def test_filter_group_id_union_with_str(self):
        """Combine queries using union with string values."""
        qs_a = Tag.objects.filter(group_id=self.group_id_str_1)
        qs_b = Tag.objects.filter(group_id=self.group_id_str_2)
        union_qs = qs_a.union(qs_b).order_by("name")
        self.assertSequenceEqual(union_qs, [self.t3, self.t4])

    def test_filter_group_id_union_with_obj(self):
        """Combine queries using union with ObjectId values."""
        qs_a = Tag.objects.filter(group_id=self.group_id_obj_1)
        qs_b = Tag.objects.filter(group_id=self.group_id_obj_2)
        union_qs = qs_a.union(qs_b).order_by("name")
        self.assertSequenceEqual(union_qs, [self.t3, self.t4])

    def test_filter_invalid_object_id(self):
        msg = "“value1” is not a valid Object Id.'"
        with self.assertRaisesMessage(ValidationError, msg):
            Tag.objects.filter(group_id="value1")

    def test_values_in_subquery(self):
        # If a values() queryset is used, then the given values will be used
        # instead of forcing use of the relation's field.
        o1 = Order.objects.create()
        o2 = Order.objects.create()
        oi1 = OrderItem.objects.create(order=o1, status=None)
        oi1.status = oi1.pk
        oi1.save()
        OrderItem.objects.create(order=o2, status=None)
        # The query below should match o1 as it has related order_item with
        # id == status.
        self.assertSequenceEqual(
            Order.objects.filter(items__in=OrderItem.objects.values_list("status")),
            [o1],
        )
