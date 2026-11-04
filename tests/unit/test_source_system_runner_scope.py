from pathlib import Path
import subprocess

import pytest

from tools.run_source_system_tests import (
    D4_FINAL_TESTS,
    code_version,
    consumer_scope,
    executed_consumer_scope,
    junit_counts,
    select_tests,
)


def test_d4_final_keeps_its_mandatory_suite() -> None:
    assert select_tests(None, d4_final=True) == list(D4_FINAL_TESTS)
    with pytest.raises(ValueError, match="cannot replace the mandatory"):
        select_tests(["tests/unit/test_document_layer_isolation.py"], d4_final=True)


def test_audit_root_alone_does_not_claim_audit_coverage() -> None:
    roots = {"revenue-forecast-audit": Path("audit")}
    consumers, coverage, excluded = consumer_scope(
        ["tests/unit/test_document_layer_isolation.py"], roots
    )
    assert "audit" not in consumers
    assert "audit" not in coverage
    assert any("no matching test selected" in item for item in excluded)


def test_audit_is_counted_only_when_its_integration_test_is_selected() -> None:
    roots = {"revenue-forecast-audit": Path("audit")}
    consumers, coverage, excluded = consumer_scope(
        ["integration/revenue_forecast_audit/test_current_public_bundle_import.py::test_public_bundle"],
        roots,
    )
    assert "audit" in consumers
    assert coverage["audit"] == [
        "integration/revenue_forecast_audit/test_current_public_bundle_import.py"
    ]
    assert not any(item.startswith("audit:") for item in excluded)


def test_parent_segment_cannot_mislabel_a_consumer_test() -> None:
    roots = {"revenue-forecast": Path("rf"), "filing-fetch": Path("ff"), "earnings-transcripts": Path("et")}
    consumers, coverage, _ = consumer_scope(
        ["integration/revenue_forecast/../filing_fetch/test_transcript_original_roundtrip.py"], roots
    )
    assert "rf" not in consumers
    assert consumers == ["filing-fetch", "earnings-transcripts"]
    assert coverage["filing-fetch"] == ["integration/filing_fetch/test_transcript_original_roundtrip.py"]


def test_selected_but_skipped_test_does_not_count_as_executed_consumer() -> None:
    roots = {"revenue-forecast-audit": Path("audit")}
    selected = {"audit": ["integration/revenue_forecast_audit/test_current_public_bundle_import.py"]}
    counts = {
        "integration.revenue_forecast_audit.test_current_public_bundle_import": {
            "total": 2,
            "skipped": 2,
            "failed": 0,
            "errors": 0,
        }
    }
    consumers, coverage, excluded = executed_consumer_scope(selected, counts, roots, collect_only=False)
    assert consumers == []
    assert coverage == {}
    assert any("without a passing test case" in item for item in excluded)


def test_consumer_requires_a_passing_case_in_every_selected_file() -> None:
    roots = {"revenue-forecast": Path("rf")}
    selected = {
        "rf": [
            "integration/revenue_forecast/test_d4_rf_consumption.py",
            "integration/revenue_forecast/test_source_ref_v2_three_repo_e2e.py",
        ]
    }
    counts = {
        "integration.revenue_forecast.test_d4_rf_consumption": {
            "total": 1,
            "skipped": 0,
            "failed": 0,
            "errors": 0,
        }
    }
    consumers, coverage, excluded = executed_consumer_scope(selected, counts, roots, collect_only=False)
    assert consumers == []
    assert coverage == {}
    assert any("test_source_ref_v2_three_repo_e2e.py" in item for item in excluded)


def test_junit_counts_expose_skips_instead_of_treating_them_as_passes(tmp_path: Path) -> None:
    report = tmp_path / "junit.xml"
    report.write_text(
        '<testsuite><testcase/><testcase><skipped message="not run"/></testcase></testsuite>',
        encoding="utf-8",
    )
    assert junit_counts(report) == {
        "total": 2,
        "skipped": 1,
        "failed": 0,
        "errors": 0,
        "by_module": {"": {"total": 2, "skipped": 1, "failed": 0, "errors": 0}},
        "nodeids": ["::", "::"],
    }


def test_code_version_includes_root_level_python_modules(tmp_path: Path) -> None:
    def git(*args: str) -> None:
        subprocess.run(["git", "-C", str(tmp_path), *args], check=True, capture_output=True)

    git("init", "-q")
    git("config", "user.name", "D4 Test")
    git("config", "user.email", "d4-test@example.invalid")
    module = tmp_path / "transcript_tool.py"
    module.write_text("VALUE = 1\n", encoding="utf-8")
    git("add", "transcript_tool.py")
    git("commit", "-qm", "fixture")
    before = code_version(tmp_path)
    module.write_text("VALUE = 2\n", encoding="utf-8")
    after = code_version(tmp_path)
    assert before["tracked_diff_sha256"] != after["tracked_diff_sha256"]
    untracked = tmp_path / "provider_fixture.py"
    untracked.write_text("VALUE = 3\n", encoding="utf-8")
    assert "provider_fixture.py" in code_version(tmp_path)["new_files"]
