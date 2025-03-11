from itertools import chain

from django.core.exceptions import FieldError
from django.db import NotSupportedError, models

from .managers import EmbeddedModelManager, MultiMongoManager


class EmbeddedModel(models.Model):
    objects = EmbeddedModelManager()

    class Meta:
        abstract = True

    def delete(self, *args, **kwargs):
        raise NotSupportedError("EmbeddedModels cannot be deleted.")

    def save(self, *args, **kwargs):
        raise NotSupportedError("EmbeddedModels cannot be saved.")


class ModelBaseOverride(models.base.ModelBase):
    __excluded_fieldnames = ("_t", "id")

    def __new__(cls, name, bases, attrs, **kwargs):
        """An override to the ModelBase which inspects inherited Model
        definitions and passes down the field names and table reference
        from parent to child model.
        ** REMAINING TODO
        - Handle Index Creation
        - Tests
        """
        parents = [b for b in bases if isinstance(b, models.base.ModelBase)]

        # if no ModelBase instances found, this is the first inherited MultiModel
        if not parents:
            return super().__new__(cls, name, bases, attrs, **kwargs)

        # Recursively fetch all fields of a class.
        # Only conclude the loop when we get the MultiModel class
        # We cannot explicitly pass a reference to the MultiModel class
        # because this builds a circluar dependency
        holder = bases
        traverse = holder[0]
        if traverse.__name__ != "MultiModel" and hasattr(traverse, "_meta"):
            while traverse and traverse.__name__ != "MultiModel" and hasattr(traverse, "_meta"):
                traverse = traverse._meta._bases[0] if traverse._meta._bases else None
            holder = (traverse,)

        parent_fields = []

        # Set up managed + default db if not set
        if hasattr(parents[0], "_meta") and parents[0].__name__ != "MultiModel":
            if not attrs.get("Meta"):

                class Meta:
                    db_table = parents[0]._meta.db_table
                    managed = False

                attrs["Meta"] = Meta()

            elif meta := attrs.get("Meta"):
                if not getattr(meta, "db_table", None):
                    meta.db_table = parents[0]._meta.db_table
                if not getattr(meta, "managed", None):
                    meta.managed = False
            parent_fields = set(parents[0]._meta.local_fields + parents[0]._meta.local_many_to_many)

        # The parent class will not be passed to the __new__ construction
        # because we will leverage Django's multi-table inheritance
        # which would lead to more complications on field resolution
        new_attrs = {**attrs}

        for field in parent_fields:
            if not models.base._has_contribute_to_class(field):
                if field.name in new_attrs:
                    raise FieldError(
                        f"Local field {field.name!r} in class {name!r} clashes with field of "
                        f"the same name from base class {parents[0].__name__!r}."
                    )
                new_attrs[field.name] = field

        # Construct new class without passing the parent reference, but adding
        # every new (derived) attribute to the django class
        new_cls = super().__new__(cls, name, holder, new_attrs, **kwargs)

        new_fields = chain(
            new_cls._meta.local_fields,
            new_cls._meta.local_many_to_many,
            new_cls._meta.private_fields,
        )
        field_names = {f.name for f in new_fields}

        for field in parent_fields:
            if field.primary_key or field.name in ModelBaseOverride.__excluded_fieldnames:
                continue
            if models.base._has_contribute_to_class(field):
                if (
                    field.name in field_names
                    and field.name not in ModelBaseOverride.__excluded_fieldnames
                ):
                    raise FieldError(
                        f"Local field {field.name!r} in class {name!r} clashes with field of "
                        f"the same name from base class {parents[0].__name__!r}."
                    )

                # if not hasattr(new_cls, field.name):
                new_cls.add_to_class(field.name, field)
        # Add each value as a subclass to its parent MultiModel object
        for _base in parents:
            # equivalent of if _base is MultiModel
            if hasattr(_base, "_subclasses"):
                _base._subclasses.setdefault(_base, []).append(new_cls)

        new_cls._meta._bases = parents
        new_cls._meta.parents = {}
        return new_cls


class MultiModel(models.Model, metaclass=ModelBaseOverride):
    """Manager handles tracking all inherited subclasses to be used in the MultiMongoManager query"""

    _subclasses = {}

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        for _base in cls.__bases__:
            if issubclass(_base, MultiModel):
                MultiModel._subclasses.setdefault(_base, []).append(cls)

    # Get all the subclasses for my model
    @classmethod
    def subclasses(cls):
        stack = [cls]
        acc = set()
        while stack:
            node = stack.pop()
            stack.extend(cls._subclasses.get(node, []))
            acc.add(node)
        return [obj.__name__ for obj in acc]

    _t = models.CharField(max_length=255, editable=False)
    objects = MultiMongoManager()

    # Save the classname as the _t before saving
    def save(self, *args, **kwargs):
        if not self._t:
            self._t = self.__class__.__name__
        super().save(*args, **kwargs)

    class Meta:
        abstract = True
