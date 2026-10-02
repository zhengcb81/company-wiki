"""Emit bounded GitHub Actions annotations from a pytest JUnit report."""

from __future__ import annotations

import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

MAX_ANNOTATIONS = 25


def _escape_command_data(value: str) -> str:
    return value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def _failed_cases(report_path: Path) -> list[tuple[str, str, str]] | None:
    try:
        root = ET.parse(report_path).getroot()
    except (OSError, ET.ParseError):
        return None

    failures: list[tuple[str, str, str]] = []
    for case in root.iter("testcase"):
        if case.find("failure") is None and case.find("error") is None:
            continue

        file_name = case.get("file", "")
        if file_name and os.path.isabs(file_name):
            file_name = os.path.relpath(file_name, Path.cwd())
        test_name = case.get("name", "unknown test")
        if file_name:
            node_id = f"{file_name}::{test_name}"
        else:
            node_id = f"{case.get('classname', 'unknown')}::{test_name}"
        failures.append((file_name, case.get("line", ""), node_id))
    return failures


def main(report_path: str) -> int:
    failures = _failed_cases(Path(report_path))
    if failures is None:
        print(
            "::error title=Unit test diagnostics::JUnit report unavailable; "
            "inspect the authenticated job log"
        )
        return 0
    if not failures:
        print(
            "::error title=Unit test diagnostics::pytest failed without a "
            "testcase entry in JUnit report"
        )
        return 0

    for file_name, line, node_id in failures[:MAX_ANNOTATIONS]:
        properties = f" file={_escape_command_data(file_name)}" if file_name else ""
        if line.isdigit():
            properties += f",line={line}"
        print(
            f"::error{properties},title=Failed unit test::"
            f"{_escape_command_data(node_id)}"
        )
    if len(failures) > MAX_ANNOTATIONS:
        remainder = len(failures) - MAX_ANNOTATIONS
        print(f"::error title=Unit test diagnostics::and {remainder} more failing tests")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: summarize_junit_failures.py JUNIT_XML")
    raise SystemExit(main(sys.argv[1]))
