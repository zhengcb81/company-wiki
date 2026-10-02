"""Emit bounded GitHub Actions annotations from a pytest JUnit report."""

from __future__ import annotations

import os
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

MAX_ANNOTATIONS = 25


def _escape_command_data(value: str) -> str:
    return value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def _failed_cases(report_path: Path) -> list[tuple[str, str, str, str]] | None:
    try:
        root = ET.parse(report_path).getroot()
    except (OSError, ET.ParseError):
        return None

    failures: list[tuple[str, str, str, str]] = []
    for case in root.iter("testcase"):
        failure = case.find("failure")
        error = case.find("error")
        if failure is None and error is None:
            continue

        file_name = case.get("file", "")
        if file_name and os.path.isabs(file_name):
            file_name = os.path.relpath(file_name, Path.cwd())
        test_name = case.get("name", "unknown test")
        if file_name:
            node_id = f"{file_name}::{test_name}"
        else:
            node_id = f"{case.get('classname', 'unknown')}::{test_name}"
        failure_kind = failure if failure is not None else error
        assert failure_kind is not None
        declared_type = failure_kind.get("type")
        if not declared_type:
            # pytest's JUnit writer may put the exception class in `message`
            # while leaving `type` empty. Keep only a class-like prefix so the
            # diagnostic does not expose assertion text or private data.
            message = failure_kind.get("message", "")
            match = re.match(r"^([A-Za-z_][A-Za-z0-9_.]*)\s*:", message)
            declared_type = match.group(1) if match else "unknown_error"
        error_type = declared_type.rsplit(".", maxsplit=1)[-1]
        error_type = "".join(char for char in error_type if char.isalnum() or char == "_")
        failures.append((file_name, case.get("line", ""), node_id, error_type))
    if not failures:
        suites = [element for element in root.iter() if element.tag.endswith("testsuite")]
        suite_errors = sum(int(suite.get("errors", "0")) for suite in suites)
        suite_failures = sum(int(suite.get("failures", "0")) for suite in suites)
        if suite_errors or suite_failures:
            count = suite_errors + suite_failures
            failures.append(
                ("", "", f"pytest collection/runtime failures ({count})", "collection")
            )
    return failures


def _append_step_summary(lines: list[str]) -> None:
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return
    try:
        with Path(summary_path).open("a", encoding="utf-8") as summary:
            summary.write("\n".join(lines) + "\n")
    except OSError:
        print("::warning title=Unit test diagnostics::Could not write GITHUB_STEP_SUMMARY")


def main(report_path: str) -> int:
    suite_name = os.environ.get("TEST_SUITE_NAME", "tests")
    failures = _failed_cases(Path(report_path))
    if failures is None:
        message = "JUnit report unavailable or invalid; inspect the authenticated job log"
        print(f"::error::{_escape_command_data(message)}")
        _append_step_summary([f"## {suite_name} JUnit report unavailable", "", message])
        return 0
    if not failures:
        if os.environ.get("TEST_SUITE_OUTCOME") == "failure":
            message = (
                f"{suite_name} pytest exited nonzero but JUnit contains no failing testcase; "
                "inspect the authenticated job log"
            )
            print(f"::error::{_escape_command_data(message)}")
            _append_step_summary([f"## {suite_name} failure details unavailable", "", message])
        return 0

    summary_lines = [f"## Failed {suite_name}", ""]
    for file_name, line, node_id, error_type in failures[:MAX_ANNOTATIONS]:
        properties = f" file={_escape_command_data(file_name)}" if file_name else ""
        if line.isdigit():
            properties += f",line={line}"
        diagnostic = f"{node_id} [{error_type}]"
        print(
            f"::error{properties}::"
            f"{_escape_command_data(diagnostic)}"
        )
        markdown_node_id = node_id.replace("`", "\\`")
        summary_lines.append(f"- `{markdown_node_id}` [{error_type}]")
    if len(failures) > MAX_ANNOTATIONS:
        remainder = len(failures) - MAX_ANNOTATIONS
        print(f"::error::and {remainder} more failing tests")
        summary_lines.extend(["", f"And {remainder} more failing tests."])
    _append_step_summary(summary_lines)
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: summarize_junit_failures.py JUNIT_XML")
    raise SystemExit(main(sys.argv[1]))
