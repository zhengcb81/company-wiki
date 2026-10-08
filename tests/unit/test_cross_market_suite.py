"""Regression harness correctness: a broken or omitted stage must stay visible."""
import stat
from pathlib import PureWindowsPath
from types import SimpleNamespace

import pytest

from tools.cross_market_suite.core import (
    compare_reports, domain_checks, isolated_directory, safe_child, summarize,
)


def report(status, *, mode="replay", digest="a", check="1"):
    return {"mode": mode, "spec_sha256": digest, "checkpoints_sha256": check,
            "checks": [{"case": "US-MSFT", "id": "acquisition", "status": status}]}


@pytest.mark.parametrize("state", ["FAIL", "BLOCKED", "NOT_RUN"])
def test_incomplete_work_never_becomes_pass(state):
    assert summarize(report(state)["checks"]) != "PASS"


def test_removed_failed_checkpoint_is_a_regression():
    after = report("PASS")
    after["checks"] = []
    assert compare_reports(report("FAIL"), after)["changes"][0]["change"] == "missing"


@pytest.mark.parametrize("field", ["mode", "spec_sha256", "checkpoints_sha256"])
def test_changed_experiment_cannot_claim_improvement(field):
    before, after = report("BLOCKED"), report("PASS")
    after[field] = "different"
    assert compare_reports(before, after)["comparable"] is False


def test_real_improvement_and_regression_are_separate():
    assert compare_reports(report("BLOCKED"), report("PASS"))["changes"][0]["change"] == "improved"
    assert compare_reports(report("PASS"), report("BLOCKED"))["changes"][0]["change"] == "regressed"


def test_faster_but_failed_run_is_not_called_a_quality_improvement():
    before, after = report("FAIL"), report("FAIL")
    before["seconds"], after["seconds"] = 100, 20
    compared = compare_reports(before, after)
    assert compared["changes"][0]["change"] == "unchanged"
    assert compared["observations"] == [{"metric": "seconds", "before": 100, "after": 20}]


def test_corrupt_portable_raw_is_refused(tmp_path):
    from tools.cross_market_suite.runner import Suite
    with isolated_directory(tmp_path) as root:
        data = root / "bundle"
        source = data / "objects" / "00" / ("0" * 64)
        source.parent.mkdir(parents=True)
        source.write_bytes(b"corrupted PDF bytes")
        suite = Suite(SimpleNamespace(mode="replay", delivery_root=data), root)
        with pytest.raises(AssertionError, match="SHA mismatch"):
            suite.raw({"sha256": "0" * 64, "object_relative": "present"})


def test_escape_is_refused(tmp_path):
    for text in ("../original.pdf", str(tmp_path / "original.pdf"),
                 str(PureWindowsPath("Z:") / "original.pdf")):
        with pytest.raises(ValueError):
            safe_child(tmp_path, text)


def test_failure_restores_owned_directory_and_preserves_sentinel(tmp_path):
    sentinel = tmp_path / "preexisting.txt"
    sentinel.write_text("keep", encoding="utf-8")
    with pytest.raises(RuntimeError):
        with isolated_directory(tmp_path) as root:
            owned = root
            (root / "downloaded.pdf").write_bytes(b"sample")
            raise RuntimeError("injected")
    assert not owned.exists()
    assert list(tmp_path.iterdir()) == [sentinel]
    assert sentinel.read_text(encoding="utf-8") == "keep"


def test_genuine_wrong_percentage_point_is_caught():
    data = {"as_of_date": "2026-10-08", "parameters": [], "segments": [],
            "management_targets": [], "growth_driver_tree": {"drivers": []},
            "sensitivity_tests": [{"parameter_id": "azure", "shock_type": "percentage_point", "shock_value": 5}]}
    expected = {"as_of_date": "2026-10-08", "parameters": {}, "segment_names": [],
                "sensitivities": {"azure": {"shock_type": "percentage_point", "shock_value": 0.05}}}
    with pytest.raises(AssertionError, match="shock"):
        domain_checks(data, expected)


def test_readonly_publication_registry_is_removed_from_owned_test_tree(tmp_path):
    with isolated_directory(tmp_path) as root:
        owned = root
        registry = root / "registry.jsonl"
        registry.write_text("sealed test registry", encoding="utf-8")
        registry.chmod(stat.S_IREAD)
    assert not owned.exists()


def test_peer_risk_must_not_turn_into_positive_company_triangulation():
    data = {"as_of_date": "2026-10-08", "parameters": [], "segments": [],
            "sensitivity_tests": [], "management_targets": [], "growth_driver_tree": {"drivers": [
                {"driver_id": "games", "evidence_nodes": [{"evidence_id": "peer", "inference_distance": "one_step"}]}]}}
    expected = {"as_of_date": "2026-10-08", "parameters": {}, "segment_names": [],
                "sensitivities": {}, "evidence_distances": {"peer": "contrary"}}
    with pytest.raises(AssertionError, match="evidence"):
        domain_checks(data, expected)


def test_undated_capacity_target_cannot_gain_an_invented_year():
    data = {"as_of_date": "2026-10-08", "parameters": [], "segments": [],
            "sensitivity_tests": [], "growth_driver_tree": {"drivers": []}, "management_targets": [
                {"target_id": "capacity", "measurement_periods": ["FY2028"], "comparison_value": None}]}
    expected = {"as_of_date": "2026-10-08", "parameters": {}, "segment_names": [], "sensitivities": {},
                "target_fields": {"capacity": {"measurement_periods": [], "comparison_value": None}}}
    with pytest.raises(AssertionError, match="target"):
        domain_checks(data, expected)
