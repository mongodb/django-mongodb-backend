from django.db import DatabaseError
from django.test import TransactionTestCase, skipIfDBFeature, skipUnlessDBFeature

from django_mongodb_backend import transaction

from .models import Reporter


@skipUnlessDBFeature("_supports_transactions")
class AtomicTests(TransactionTestCase):
    """Largely copied from Django's test/transactions."""

    available_apps = ["transactions_"]

    def test_decorator_syntax_commit(self):
        @transaction.atomic
        def make_reporter():
            return Reporter.objects.create(first_name="Tintin")

        reporter = make_reporter()
        self.assertSequenceEqual(Reporter.objects.all(), [reporter])

    def test_decorator_syntax_rollback(self):
        @transaction.atomic
        def make_reporter():
            Reporter.objects.create(first_name="Haddock")
            raise Exception("Oops, that's his last name")

        with self.assertRaisesMessage(Exception, "Oops"):
            make_reporter()
        self.assertSequenceEqual(Reporter.objects.all(), [])

    def test_alternate_decorator_syntax_commit(self):
        @transaction.atomic()
        def make_reporter():
            return Reporter.objects.create(first_name="Tintin")

        reporter = make_reporter()
        self.assertSequenceEqual(Reporter.objects.all(), [reporter])

    def test_alternate_decorator_syntax_rollback(self):
        @transaction.atomic()
        def make_reporter():
            Reporter.objects.create(first_name="Haddock")
            raise Exception("Oops, that's his last name")

        with self.assertRaisesMessage(Exception, "Oops"):
            make_reporter()
        self.assertSequenceEqual(Reporter.objects.all(), [])

    def test_commit(self):
        with transaction.atomic():
            reporter = Reporter.objects.create(first_name="Tintin")
        self.assertSequenceEqual(Reporter.objects.all(), [reporter])

    def test_rollback(self):
        with self.assertRaisesMessage(Exception, "Oops"), transaction.atomic():
            Reporter.objects.create(first_name="Haddock")
            raise Exception("Oops, that's his last name")
        self.assertSequenceEqual(Reporter.objects.all(), [])

    def test_nested_commit_commit(self):
        with transaction.atomic():
            reporter1 = Reporter.objects.create(first_name="Tintin")
            with transaction.atomic():
                reporter2 = Reporter.objects.create(first_name="Archibald", last_name="Haddock")
        self.assertSequenceEqual(Reporter.objects.all(), [reporter2, reporter1])

    def test_nested_rollback_commit(self):
        with self.assertRaisesMessage(Exception, "Oops"), transaction.atomic():
            Reporter.objects.create(last_name="Tintin")
            with transaction.atomic():
                Reporter.objects.create(last_name="Haddock")
            raise Exception("Oops, that's his first name")
        self.assertSequenceEqual(Reporter.objects.all(), [])

    def test_nested_rollback_rollback(self):
        with self.assertRaisesMessage(Exception, "Oops"), transaction.atomic():
            Reporter.objects.create(last_name="Tintin")
            with self.assertRaisesMessage(Exception, "Oops"):
                with transaction.atomic():
                    Reporter.objects.create(first_name="Haddock")
                raise Exception("Oops, that's his last name")
            raise Exception("Oops, that's his first name")
        self.assertSequenceEqual(Reporter.objects.all(), [])

    def test_reuse_commit_commit(self):
        atomic = transaction.atomic()
        with atomic:
            reporter1 = Reporter.objects.create(first_name="Tintin")
            with atomic:
                reporter2 = Reporter.objects.create(first_name="Archibald", last_name="Haddock")
        self.assertSequenceEqual(Reporter.objects.all(), [reporter2, reporter1])

    def test_reuse_rollback_commit(self):
        atomic = transaction.atomic()
        with self.assertRaisesMessage(Exception, "Oops"), atomic:
            Reporter.objects.create(last_name="Tintin")
            with atomic:
                Reporter.objects.create(last_name="Haddock")
            raise Exception("Oops, that's his first name")
        self.assertSequenceEqual(Reporter.objects.all(), [])

    def test_reuse_rollback_rollback(self):
        atomic = transaction.atomic()
        with self.assertRaisesMessage(Exception, "Oops"), atomic:
            Reporter.objects.create(last_name="Tintin")
            with self.assertRaisesMessage(Exception, "Oops"):
                with atomic:
                    Reporter.objects.create(first_name="Haddock")
                raise Exception("Oops, that's his last name")
            raise Exception("Oops, that's his first name")
        self.assertSequenceEqual(Reporter.objects.all(), [])

    def test_rollback_update(self):
        r = Reporter.objects.create(last_name="Tintin")
        with self.assertRaisesMessage(Exception, "Oops"), transaction.atomic():
            Reporter.objects.update(last_name="Haddock")
            # The update is visible in the transaction.
            r.refresh_from_db()
            self.assertEqual(r.last_name, "Haddock")
            raise Exception("Oops")
        # But is now rolled back.
        r.refresh_from_db()
        self.assertEqual(r.last_name, "Tintin")

    def test_rollback_delete(self):
        r = Reporter.objects.create(last_name="Tintin")
        with self.assertRaisesMessage(Exception, "Oops"), transaction.atomic():
            Reporter.objects.all().delete()
            raise Exception("Oops")
        self.assertSequenceEqual(Reporter.objects.all(), [r])

    def test_wrap_callable_instance(self):
        """Atomic can wrap callable instances."""

        class Callable:
            def __call__(self):
                pass

        transaction.atomic(Callable())  # Must not raise an exception


@skipIfDBFeature("_supports_transactions")
class AtomicNotSupportedTests(TransactionTestCase):
    available_apps = ["transactions_"]

    def test_not_supported(self):
        # If transactions aren't supported, MongoDB raises an error:
        # "Transaction numbers are only allowed on a replica set member or mongos"
        with self.assertRaises(DatabaseError), transaction.atomic():
            Reporter.objects.create(first_name="Haddock")
