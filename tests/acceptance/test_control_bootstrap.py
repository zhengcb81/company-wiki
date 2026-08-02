"""Reviewer-owned controls: eight known-bad cases must fail and one good case must pass."""

import hashlib
import json
import sys
from pathlib import Path

from architecture_gate import evaluate_architecture
from clean_env_gate import is_candidate_path
from gate_runner import boundary_violations, run_commands, sha256_file, verify_lock
from gate_state import derive_state
from semantic_gate import evaluate_gold_integrity


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def test_bad_1_tampered_acceptance_lock_is_rejected(tmp_path):
    protected = tmp_path / "spec.json"
    protected.write_text("fixed", encoding="utf-8")
    lock = tmp_path / "lock.json"
    write_json(lock, {"algorithm": "sha256", "files": {"spec.json": sha256_file(protected)}})
    protected.write_text("tampered", encoding="utf-8")
    assert verify_lock(tmp_path, lock) == ["locked file hash mismatch: spec.json"]


def test_bad_2_path_outside_work_unit_allowlist_is_rejected():
    baseline = {"entries": {"allowed.py": {"sha256": "a"}, "surprise.py": {"sha256": "a"}}}
    current = {"entries": {"allowed.py": {"sha256": "b"}, "surprise.py": {"sha256": "b"}}}
    violations = boundary_violations(baseline, current, ["allowed.py"], [])
    assert violations == ["path outside Work Unit allowlist: surprise.py"]


def test_bad_3_reviewer_owned_path_change_is_rejected():
    baseline = {"entries": {"control/acceptance.json": {"sha256": "a"}}}
    current = {"entries": {"control/acceptance.json": {"sha256": "b"}}}
    violations = boundary_violations(baseline, current, ["**"], ["control/**"])
    assert violations == ["reviewer-owned path changed: control/acceptance.json"]


def test_bad_4_failed_command_cannot_be_candidate(tmp_path):
    results = run_commands(
        tmp_path,
        [{"name": "fail", "argv": [sys.executable, "-c", "raise SystemExit(7)"]}],
    )
    assert results[0]["exit_code"] == 7


def test_bad_5_production_data_is_excluded_from_clean_candidate():
    assert not is_candidate_path("companies/北方华创/raw/report.pdf")
    assert not is_candidate_path("sectors/半导体设备/wiki/行业概览.md")
    assert is_candidate_path("tests/fixtures/mini_wiki/raw/北方华创/fixture.md")


def test_bad_6_constant_success_failure_drill_is_rejected(tmp_path):
    deployment = tmp_path / "deployment.py"
    deployment.write_text("def drill():\n    return True\n", encoding="utf-8")
    config = {
        "schema_version": 1,
        "rules": [
            {
                "id": "constant-drill",
                "kind": "forbidden_regex",
                "glob": "deployment.py",
                "regex": "return\\s+True",
            }
        ],
    }
    assert evaluate_architecture(tmp_path, config)["result"] == "fail"


def make_bad_gold(tmp_path: Path) -> Path:
    gold = tmp_path / "gold"
    source = gold / "sources" / "A" / "source.md"
    source.parent.mkdir(parents=True)
    source.write_text("---\nsource_id: S1\n---\nEvidence", encoding="utf-8")
    full_text = source.read_text(encoding="utf-8")
    start = full_text.index("Evidence")
    write_json(
        gold / "annotations" / "evidence_spans.json",
        {"spans": {"S1": [{"span_id": "E1", "start": start, "end": start + 8, "text": "Evidence"}]}},
    )
    write_json(
        gold / "annotations" / "material_claims.json",
        {"claims": [{"claim_id": "C1", "source_id": "S1", "evidence_spans": ["E1"]}]},
    )
    write_json(
        gold / "annotations" / "routing_targets.json",
        {"routing": [{"source_id": "S1", "expected_targets": [{"entity_id": "A"}]}]},
    )
    write_json(gold / "annotations" / "contradictions.json", {"contradictions": []})
    write_json(
        gold / "expected" / "quality_metrics.json",
        {
            "metrics": {
                "source_coverage": {"total_sources": 1, "actual": 1.0, "target": 1.0, "status": "pass"},
                "numeric_exactness": {"actual": 0.8, "target": 0.95, "status": "pass_with_notes"},
            }
        },
    )
    return gold


def test_bad_7_below_threshold_pass_with_notes_is_rejected(tmp_path):
    result = evaluate_gold_integrity(make_bad_gold(tmp_path), min_sources=1)
    assert any(
        violation["id"] == "handwritten-status-contradicts-threshold"
        for violation in result["violations"]
    )


def test_bad_8_review_for_different_receipt_is_rejected(tmp_path):
    receipt = tmp_path / "receipt.json"
    write_json(
        receipt,
        {
            "work_unit": "WU",
            "result": "pass",
            "status": "candidate",
            "workspace_digest": "digest",
        },
    )
    review = tmp_path / "review.json"
    write_json(
        review,
        {
            "receipt_sha256": "different",
            "decision": "approved",
            "reviewer": "independent",
            "independent": True,
        },
    )
    assert derive_state(receipt, review)["state"] == "rejected"


def test_positive_control_valid_receipt_stays_candidate_without_review(tmp_path):
    receipt = tmp_path / "receipt.json"
    write_json(
        receipt,
        {
            "work_unit": "WU",
            "result": "pass",
            "status": "candidate",
            "workspace_digest": hashlib.sha256(b"tree").hexdigest(),
        },
    )
    state = derive_state(receipt)
    assert state["state"] == "candidate"
    assert state["violations"] == []
