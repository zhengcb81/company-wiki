"""Tests for privacy-bounded pytest failure annotations used by Actions."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

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


def test_first_annotation_contains_groups_beyond_platform_annotation_limit(tmp_path, capsys):
    report = tmp_path / "all-failures.xml"
    _write_report(report, case_count=30)
    assert main(str(report)) == 0
    first = capsys.readouterr().out.splitlines()[0]
    assert "Failure groups (30 failed cases)" in first
    assert "test_case_29" in first
    assert "private traceback omitted" not in first


def test_group_inventory_collapses_parameters_without_revealing_their_values(tmp_path, capsys):
    report = tmp_path / "parameterized.xml"
    suite = ET.Element("testsuite")
    for index in range(30):
        case = ET.SubElement(suite, "testcase", {
            "file": "tests/unit/test_example.py",
            "name": f"test_group[private_parameter_{index}]",
        })
        ET.SubElement(case, "failure", {"type": "AssertionError"})
    ET.ElementTree(suite).write(report, encoding="utf-8")
    assert main(str(report)) == 0
    first = capsys.readouterr().out.splitlines()[0]
    groups = first.split("Failure groups", 1)[1]
    assert "test_group [AssertionError] x30" in groups
    assert "private_parameter" not in groups


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


@pytest.mark.parametrize("stale_report", [False, True], ids=["missing-report", "stale-failure"])
def test_skipped_suite_does_not_read_a_report_or_emit_failure_annotations(
    tmp_path, capsys, monkeypatch, stale_report
):
    report = tmp_path / "previous-or-missing.xml"
    if stale_report:
        _write_report(report)
    summary = tmp_path / "step-summary.md"
    monkeypatch.setenv("TEST_SUITE_OUTCOME", "skipped")
    monkeypatch.setenv("TEST_SUITE_NAME", "contract tests")
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))

    def report_read_forbidden(*_args, **_kwargs):
        raise AssertionError("a skipped suite must not read current or stale JUnit")

    monkeypatch.setattr(ET, "parse", report_read_forbidden)
    assert main(str(report)) == 0
    output = capsys.readouterr().out
    assert "contract tests" in output and "not run" in output and "skipped" in output
    assert "::error" not in output
    content = summary.read_text(encoding="utf-8")
    assert "not run" in content and "skipped" in content
    assert "test_case_0" not in content and "Failed" not in content


@pytest.mark.parametrize("missing_report", [False, True], ids=["no-failure-detail", "no-report"])
def test_actual_failure_without_junit_detail_still_emits_error(
    tmp_path, capsys, monkeypatch, missing_report
):
    report = tmp_path / "failed.xml"
    if not missing_report:
        report.write_text('<testsuite tests="0" failures="0" errors="0"/>', encoding="utf-8")
    monkeypatch.setenv("TEST_SUITE_OUTCOME", "failure")
    assert main(str(report)) == 0
    output = capsys.readouterr().out
    assert "::error::" in output and "not run" not in output


def test_long_failure_inventory_survives_platform_message_and_annotation_limits(tmp_path, capsys):
    report = tmp_path / "long-inventory.xml"
    suite = ET.Element("testsuite")
    names = [f"test_group_{index}_" + "specific_failure_" * 5 for index in range(63)]
    for name in names:
        case = ET.SubElement(suite, "testcase", {"classname": "tests.unit.long_module", "name": name})
        ET.SubElement(case, "failure", {"type": "AssertionError", "message": "private body"})
    ET.ElementTree(suite).write(report, encoding="utf-8")
    assert main(str(report)) == 0
    annotations = [line for line in capsys.readouterr().out.splitlines() if line.startswith("::error")]
    messages = [line.split("::", 2)[2] for line in annotations]
    assert all(len(message.encode("utf-8")) <= 4096 for message in messages)
    # Actions can retain only the first ten annotations and truncate each body.
    visible = "\n".join(messages[:10])
    assert all(name in visible for name in names)
    assert "private body" not in visible


def test_annotation_bounds_cover_escaped_utf8_and_long_case_identity(tmp_path, capsys):
    report = tmp_path / "unicode-identity.xml"
    suite = ET.Element("testsuite")
    case = ET.SubElement(suite, "testcase", {
        "classname": "tests.unit.unicode", "name": "test_identity[" + "汉%\n" * 3000 + "]",
    })
    ET.SubElement(case, "failure", {"type": "AssertionError"})
    ET.ElementTree(suite).write(report, encoding="utf-8")
    assert main(str(report)) == 0
    messages = [line.split("::", 2)[2] for line in capsys.readouterr().out.splitlines()
                if line.startswith("::error")]
    assert all(len(message.encode("utf-8")) <= 4096 for message in messages)
    assert any("[truncated]" in message for message in messages)
    assert "test_identity [AssertionError] x1" in "\n".join(messages)
