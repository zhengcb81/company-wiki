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
        ET.SubElement(
            case,
            "failure",
            {"message": "private traceback omitted", "type": "AssertionError"},
        )
    ET.ElementTree(suite).write(path, encoding="utf-8", xml_declaration=True)


def test_emits_test_identity_without_failure_body(tmp_path: Path, capsys) -> None:
    report = tmp_path / "junit.xml"
    _write_report(report)

    assert main(str(report)) == 0
    output = capsys.readouterr().out
    assert "::error file=tests/unit/test_example.py,line=10::" in output
    assert "tests/unit/test_example.py::test_case_0" in output
    assert "[AssertionError]" in output
    assert "private traceback omitted" not in output


def test_extracts_only_exception_class_when_junit_type_is_missing(
    tmp_path: Path, capsys
) -> None:
    report = tmp_path / "junit-missing-type.xml"
    suite = ET.Element("testsuite")
    case = ET.SubElement(
        suite,
        "testcase",
        {"file": "tests/contract/test_example.py", "name": "test_private_failure"},
    )
    ET.SubElement(
        case,
        "failure",
        {"message": "sqlite3.OperationalError: private database detail"},
    )
    ET.ElementTree(suite).write(report, encoding="utf-8", xml_declaration=True)

    assert main(str(report)) == 0
    output = capsys.readouterr().out
    assert "[OperationalError]" in output
    assert "private database detail" not in output


def test_caps_annotations_and_reports_remaining_failure_count(
    tmp_path: Path, capsys
) -> None:
    report = tmp_path / "many-failures.xml"
    _write_report(report, case_count=30)

    assert main(str(report)) == 0
    output = capsys.readouterr().out.splitlines()
    assert sum(line.startswith("::error file=tests/unit/test_example.py,line=") for line in output) == 25
    assert output[-1] == "::error::and 5 more failing tests"


def test_missing_junit_file_keeps_original_pytest_failure_actionable(
    tmp_path: Path, capsys
) -> None:
    assert main(str(tmp_path / "missing.xml")) == 0
    output = capsys.readouterr().out
    assert "JUnit report unavailable" in output


def test_writes_only_failure_identities_to_step_summary(
    tmp_path: Path, monkeypatch
) -> None:
    report = tmp_path / "junit.xml"
    summary = tmp_path / "step-summary.md"
    _write_report(report)
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))

    assert main(str(report)) == 0
    content = summary.read_text(encoding="utf-8")
    assert "tests/unit/test_example.py::test_case_0" in content
    assert "private traceback omitted" not in content


def test_pass_report_produces_no_failure_diagnostic(tmp_path: Path, capsys) -> None:
    report = tmp_path / "passing.xml"
    suite = ET.Element("testsuite")
    ET.SubElement(suite, "testcase", {"name": "test_pass"})
    ET.ElementTree(suite).write(report, encoding="utf-8", xml_declaration=True)

    assert main(str(report)) == 0
    assert capsys.readouterr().out == ""


def test_failed_pytest_with_no_failed_case_gets_a_diagnostic(
    tmp_path: Path, capsys, monkeypatch
) -> None:
    report = tmp_path / "empty-junit.xml"
    suite = ET.Element("testsuite", {"tests": "0", "failures": "0", "errors": "0"})
    ET.ElementTree(suite).write(report, encoding="utf-8", xml_declaration=True)
    monkeypatch.setenv("TEST_SUITE_OUTCOME", "failure")
    monkeypatch.setenv("TEST_SUITE_NAME", "contract tests")

    assert main(str(report)) == 0
    output = capsys.readouterr().out
    assert "contract tests pytest exited nonzero but JUnit contains no failing testcase" in output


def test_collection_error_without_testcase_gets_a_generic_identity(
    tmp_path: Path, capsys
) -> None:
    report = tmp_path / "collection-error.xml"
    suite = ET.Element("testsuite", {"errors": "2", "tests": "0"})
    ET.ElementTree(suite).write(report, encoding="utf-8", xml_declaration=True)

    assert main(str(report)) == 0
    assert "pytest collection/runtime failures (2)" in capsys.readouterr().out


def test_collection_traceback_exposes_exception_class_without_private_body(tmp_path, capsys):
    report = tmp_path / "collection.xml"
    suite = ET.Element("testsuite", {"errors": "1"})
    case = ET.SubElement(suite, "testcase", {"name": "tests.unit.test_bounded_http"})
    error = ET.SubElement(case, "error", {"message": "collection failure"})
    error.text = "private source text\nE   ModuleNotFoundError: No module named 'httpx'\nprivate body"
    ET.ElementTree(suite).write(report, encoding="utf-8")
    assert main(str(report)) == 0
    output = capsys.readouterr().out
    assert "[ModuleNotFoundError]" in output
    assert "private" not in output and "No module named" not in output
