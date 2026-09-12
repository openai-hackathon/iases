"""Record all pytest phases, including xfail, for the manifest validator."""

import json
import os
from pathlib import Path

_collected = []
_reports = {}


def pytest_collection_finish(session):
    _collected.extend(item.nodeid for item in session.items)


def pytest_runtest_logreport(report):
    entry = _reports.setdefault(report.nodeid, {"phases": {}})
    entry["phases"][report.when] = report.outcome
    if hasattr(report, "wasxfail"):
        entry["expected_failure"] = True
    if report.failed:
        entry["diagnostic"] = str(report.longrepr)[-12000:]


def pytest_sessionfinish(session, exitstatus):
    results = {}
    for node in _collected:
        value = _reports.get(node, {})
        phases = value.get("phases", {})
        if value.get("expected_failure"):
            status = "xfail"
        elif phases.get("setup") == "failed" or phases.get("teardown") == "failed":
            status = "error"
        elif "failed" in phases.values():
            status = "failed"
        elif "skipped" in phases.values():
            status = "skipped"
        elif all(
            phases.get(phase) == "passed" for phase in ("setup", "call", "teardown")
        ):
            status = "passed"
        else:
            status = "missing"
        results[node] = {"status": status, **value}
    Path(os.environ["TSMC_REPORT_PATH"]).write_text(
        json.dumps(
            {
                "collected": _collected,
                "exit_code": int(exitstatus),
                "tests": results,
            },
            ensure_ascii=False,
        )
    )
