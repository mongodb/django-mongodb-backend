from django.test.runner import DiscoverRunner

from .base import write_output_file


class TestRunner(DiscoverRunner):
    def teardown_test_environment(self, **kwargs):
        write_output_file()
        super().teardown_test_environment(**kwargs)
