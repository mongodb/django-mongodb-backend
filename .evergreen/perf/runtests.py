import json
import logging
import os
import shlex
import subprocess
import sys
from datetime import datetime
from pathlib import Path

LOGGER = logging.getLogger("test")
logging.basicConfig(level=logging.INFO, format="%(levelname)-8s %(message)s")
OUTPUT_FILE = os.environ.get("OUTPUT_FILE", "results.json")


def format_output(start_time: datetime):
    """Format the output from the performance tests into a report.json file."""
    end_time = datetime.now()
    elapsed_secs = (end_time - start_time).total_seconds()
    with open(OUTPUT_FILE) as fid:  # noqa: PTH123
        results = json.load(fid)
    LOGGER.info("%s:\n%s", OUTPUT_FILE, json.dumps(results, indent=2))

    results = {
        "status": "PASS",
        "exit_code": 0,
        "test_file": "BenchmarkTests",
        "start": int(start_time.timestamp()),
        "end": int(end_time.timestamp()),
        "elapsed": elapsed_secs,
    }
    report = {"results": [results]}

    LOGGER.info("report.json\n%s", json.dumps(report, indent=2))

    with open("report.json", "w", newline="\n") as fid:  # noqa: PTH123
        json.dump(report, fid)


def run_command(cmd: str | list[str], **kwargs) -> None:
    """Run a shell command. Exit on failure."""
    if isinstance(cmd, list):
        cmd = " ".join(cmd)
    LOGGER.info("Running command '%s'...", cmd)
    kwargs.setdefault("check", True)
    try:
        subprocess.run(shlex.split(cmd), **kwargs)  # noqa: PLW1510, S603
    except subprocess.CalledProcessError as e:
        LOGGER.error(e.output)
        LOGGER.error(str(e))
        sys.exit(e.returncode)
    LOGGER.info("Running command '%s'... done.", cmd)


start_time = datetime.now()
ROOT = Path(__file__).absolute().parent.parent.parent
data_dir = ROOT / "specifications/source/benchmarking/odm-data"
if not data_dir.exists():
    run_command("git clone --depth 1 https://github.com/mongodb/specifications.git")
    run_command("tar xf flat_models.tgz", cwd=data_dir)
    run_command("tar xf nested_models.tgz", cwd=data_dir)

os.chdir("performance_tests")
start_time = datetime.now()
run_command(
    "python runtests.py",
    env=os.environ
    | {
        "DJANGO_MONGODB_PERFORMANCE_TEST_DATA_PATH": str(data_dir),
        "OUTPUT_FILE": OUTPUT_FILE,
    },
)
format_output(start_time)
