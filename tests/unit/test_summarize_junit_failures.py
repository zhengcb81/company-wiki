"""Tests for privacy-bounded pytest failure annotations used by Actions."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from tools.summarize_junit_failures import main


def _write_report(path: Path, case_count: int = 1) -> None:
    suite = ET.Element("testsuite")
    for index in range(case_count):
        case = ET.SubElement(
            suite,
            "testcase",
            {
                "classname": "tests.unit.example.TestExample",
                "file": "tests/unit/test_example.py",
                "line": str(index + 10),
                "name": f"test_case_{index}",
            },
        )
        ET.SubElement(case, "failure", {"message": "private traceback omitted"})
    ET.ElementTree(suite).write(path, encoding="utf-8", xml_declaration=True)


def test_emits_test_identity_without_failure_body(tmp_path: Path, capsys) -> None:
    report = tmp_path / "junit.xml"
    _write_report(report)

    assert main(str(report)) == 0
    output = capsys.readouterr().out
    assert "::error file=tests/unit/test_example.py,line=10,title=Failed unit test::" in output
    assert "tests/unit/test_example.py::test_case_0" in output
    assert "private traceback omitted" not in output


def test_caps_annotations_and_reports_remaining_failure_count(
    tmp_path: Path, capsys
) -> None:
    report = tmp_path / "many-failures.xml"
    _write_report(report, case_count=30)

    assert main(str(report)) == 0
    output = capsys.readouterr().out.splitlines()
    assert sum("title=Failed unit test" in line for line in output) == 25
    assert output[-1] == "::error title=Unit test diagnostics::and 5 more failing tests"


def test_missing_junit_file_keeps_original_pytest_failure_actionable(
    tmp_path: Path, capsys
) -> None:
    assert main(str(tmp_path / "missing.xml")) == 0
    assert "JUnit report unavailable" in capsys.readouterr().out
