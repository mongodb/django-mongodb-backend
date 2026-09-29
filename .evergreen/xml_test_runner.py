"""
Test runner that writes a JUnit XML report per test class so that Evergreen's
attach.xunit_results command can report the status of each test individually.

Wraps unittest-xml-reporting's Django runner with a workaround for test
classes that shadow TestCase.id() with a plain attribute.
"""

import unittest

from xmlrunner.extra.djangotestrunner import XMLTestRunner
from xmlrunner.result import _TestInfo, _XMLTestResult


class _SafeTestInfo(_TestInfo):
    def __init__(self, test_result, test_method, *args, **kwargs):
        test_id = getattr(test_method, "id", None)
        if test_id is not None and not callable(test_id):
            if isinstance(test_method, unittest.TestCase):
                # Bypass the shadowing attribute so the real id is reported.
                test_method.id = lambda: unittest.TestCase.id(test_method)
            else:
                test_method.id = lambda: str(test_id)
        super().__init__(test_result, test_method, *args, **kwargs)


class _SafeXMLTestResult(_XMLTestResult):
    def __init__(self, *args, **kwargs):
        # _XMLTestResult.__init__ replaces the infoclass class attribute
        # with _TestInfo unless it's passed as a constructor argument.
        kwargs.setdefault("infoclass", _SafeTestInfo)
        super().__init__(*args, **kwargs)


class EvergreenXMLTestRunner(XMLTestRunner):
    def get_resultclass(self):
        return _SafeXMLTestResult
