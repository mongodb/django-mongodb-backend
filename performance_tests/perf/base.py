"""Tests for the MongoDB ODM Performance Benchmark Spec.

For instructions, see docs/internals/contributing/performance-tests.rst.
"""

import json
import os
import time
import warnings
from pathlib import Path

if os.environ.get("FASTBENCH"):
    # Each benchmark will run for at least NUM_ITERATIONS and at least
    # MIN_ITERATION_TIME seconds.
    NUM_ITERATIONS = 1
    MIN_ITERATION_TIME = 5
    # A benchmark times out (exiting early with a warning) if it runs for more
    # than MAX_ITERATION_TIME seconds but doesn't reach NUM_ITERATIONS.
    MAX_ITERATION_TIME = 10
    # The number of model instances to use for each benchmark.
    NUM_DOCS = 1000
else:
    NUM_ITERATIONS = 2
    MIN_ITERATION_TIME = 30
    MAX_ITERATION_TIME = 300
    NUM_DOCS = 10000


class Timer:
    def __enter__(self):
        self.start = time.monotonic()
        return self

    def __exit__(self, *args):
        self.end = time.monotonic()
        self.interval = self.end - self.start


# The tearDown() method of each PerformanceTest appends metrics to this list.
# The test runner uses it at the end of the test suite to write the output
# file.
result_data = []


def write_output_file():
    if not result_data:
        return
    output = json.dumps(result_data, indent=4)
    if OUTPUT_FILE := os.environ.get("OUTPUT_FILE"):
        with open(OUTPUT_FILE, "w") as opf:  # noqa: PTH123
            opf.write(output)
    else:
        print(output)  # noqa: T201


# Copied from the driver benchmarking suite.
class PerformanceTest:
    dataset: str
    data_size: int
    test_data_path = os.environ.get(
        "DJANGO_MONGODB_PERFORMANCE_TEST_DATA_PATH",
        Path(os.path.realpath(__file__)).parent.parent / "odm-data",
    )
    num_docs = NUM_DOCS

    def setUp(self):
        self.setup_time = time.monotonic()

    def tearDown(self):
        duration = time.monotonic() - self.setup_time
        # Remove "Test" so that TestMyTestName is reported as "MyTestName".
        name = self.__class__.__name__[4:]
        median = self.percentile(50)
        if median is None:
            # Test failed.
            return
        megabytes_per_sec = self.data_size / median / 1000000
        print(  # noqa: T201
            f"Completed {self.__class__.__name__} {megabytes_per_sec:.3f} MB/s, "
            f"MEDIAN={self.percentile(50):.3f}s, "
            f"total time={duration:.3f}s, iterations={len(self.results)}"
        )
        result_data.append(
            {
                "info": {
                    "test_name": name,
                },
                "metrics": [
                    {
                        "name": "megabytes_per_sec",
                        "type": "MEDIAN",
                        "value": megabytes_per_sec,
                        "metadata": {
                            "improvement_direction": "up",
                            "measurement_unit": "megabytes_per_second",
                        },
                    },
                ],
            }
        )

    def before(self):
        pass

    def do_task(self):
        raise NotImplementedError

    def after(self):
        pass

    def percentile(self, percentile):
        if hasattr(self, "results"):
            sorted_results = sorted(self.results)
            percentile_index = int(len(sorted_results) * percentile / 100) - 1
            return sorted_results[percentile_index]
        # Test failed.
        return None

    def runTest(self):
        results = []
        start = time.monotonic()
        i = 0
        while True:
            i += 1
            self.before()
            with Timer() as timer:
                self.do_task()
            self.after()
            results.append(timer.interval)
            duration = time.monotonic() - start
            if duration > MIN_ITERATION_TIME and i >= NUM_ITERATIONS:
                break
            if duration > MAX_ITERATION_TIME:
                with warnings.catch_warnings():
                    warnings.simplefilter("default")
                    warnings.warn(
                        f"{self.__class__.__name__} timed out after {MAX_ITERATION_TIME}s, "
                        f"completed {i}/{NUM_ITERATIONS} iterations.",
                        stacklevel=2,
                    )
                break
        self.results = results
