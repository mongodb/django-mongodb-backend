import json
import logging
import os
import shlex
import subprocess
import sys
from datetime import datetime

LOGGER = logging.getLogger("test")
logging.basicConfig(level=logging.INFO, format="%(levelname)-8s %(message)s")
OUTPUT_FILE = os.environ.get("OUTPUT_FILE")


def handle_perf(start_time: datetime):
    end_time = datetime.now()
    elapsed_secs = (end_time - start_time).total_seconds()
    with open(OUTPUT_FILE) as fid:  # noqa: PTH123
        results = json.load(fid)
    LOGGER.info("results.json:\n%s", json.dumps(results, indent=2))

    results = {
        "status": "PASS",
        "exit_code": 0,
        "test_file": "BenchMarkTests",
        "start": int(start_time.timestamp()),
        "end": int(end_time.timestamp()),
        "elapsed": elapsed_secs,
    }
    report = {"failures": 0, "results": [results]}

    LOGGER.info("report.json\n%s", json.dumps(report, indent=2))

    with open("report.json", "w", newline="\n") as fid:  # noqa: PTH123
        json.dump(report, fid)


def run_command(cmd: str | list[str], **kwargs) -> None:
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


os.chdir("tests/performance")

start_time = datetime.now()
run_command(["python manage.py test"])
handle_perf(start_time)
