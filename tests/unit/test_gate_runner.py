import json
import subprocess
import sys
from pathlib import Path

from gate_runner import (
    boundary_violations,
    evaluate_work_unit,
    sha256_file,
    verify_lock,
    workspace_snapshot,
)


def init_repo(path: Path) -> None:
    subprocess.run(["git", "init", "--quiet"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.email", "gate@example.invalid"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "Gate Test"], cwd=path, check=True)
    (path / "tracked.txt").write_text("baseline", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.txt"], cwd=path, check=True)
    subprocess.run(["git", "commit", "--quiet", "-m", "baseline"], cwd=path, check=True)


def test_lock_accepts_matching_files_and_rejects_tampering(tmp_path):
    protected = tmp_path / "protected.txt"
    protected.write_text("fixed", encoding="utf-8")
    lock = tmp_path / "lock.json"
    lock.write_text(
        json.dumps({"algorithm": "sha256", "files": {"protected.txt": sha256_file(protected)}}),
        encoding="utf-8",
    )
    assert verify_lock(tmp_path, lock) == []
    protected.write_text("tampered", encoding="utf-8")
    assert "locked file hash mismatch: protected.txt" in verify_lock(tmp_path, lock)


def test_boundary_allows_only_declared_paths(tmp_path):
    init_repo(tmp_path)
    baseline = workspace_snapshot(tmp_path)
    (tmp_path / "tracked.txt").write_text("allowed", encoding="utf-8")
    current = workspace_snapshot(tmp_path)
    assert boundary_violations(baseline, current, ["tracked.txt"], []) == []
    (tmp_path / "surprise.txt").write_text("unexpected", encoding="utf-8")
    current = workspace_snapshot(tmp_path)
    assert "path outside Work Unit allowlist: surprise.txt" in boundary_violations(
        baseline, current, ["tracked.txt"], []
    )


def test_reviewer_owned_path_is_rejected_even_when_allowlisted(tmp_path):
    init_repo(tmp_path)
    protected = tmp_path / "control" / "acceptance.json"
    protected.parent.mkdir()
    protected.write_text("{}", encoding="utf-8")
    baseline = workspace_snapshot(tmp_path)
    protected.write_text('{"changed": true}', encoding="utf-8")
    current = workspace_snapshot(tmp_path)
    violations = boundary_violations(baseline, current, ["**"], ["control/**"])
    assert violations == ["reviewer-owned path changed: control/acceptance.json"]


def test_boundary_rejects_git_index_changes(tmp_path):
    init_repo(tmp_path)
    baseline = workspace_snapshot(tmp_path)
    (tmp_path / "tracked.txt").write_text("staged", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.txt"], cwd=tmp_path, check=True)
    current = workspace_snapshot(tmp_path)
    assert "git index changed outside Work Unit boundary" in boundary_violations(
        baseline, current, ["tracked.txt"], []
    )


def test_workspace_snapshot_excludes_codegraph_runtime_lock(tmp_path):
    init_repo(tmp_path)
    lock = tmp_path / ".codegraph" / "codegraph.lock"
    lock.parent.mkdir()
    lock.write_text("one", encoding="utf-8")
    before = workspace_snapshot(tmp_path)
    lock.write_text("two", encoding="utf-8")
    after = workspace_snapshot(tmp_path)
    assert ".codegraph/codegraph.lock" not in before["entries"]
    assert before["digest"] == after["digest"]


def test_gate_failure_never_produces_candidate_status(tmp_path):
    init_repo(tmp_path)
    control = tmp_path / "control"
    artifacts = tmp_path / "artifacts"
    control.mkdir()
    artifacts.mkdir()
    acceptance = {
        "reviewer_owned_paths": ["control/acceptance.json", "control/acceptance.lock.json"]
    }
    acceptance_path = control / "acceptance.json"
    acceptance_path.write_text(json.dumps(acceptance), encoding="utf-8")
    lock_path = control / "acceptance.lock.json"
    lock_path.write_text(
        json.dumps(
            {
                "algorithm": "sha256",
                "files": {
                    "control/acceptance.json": sha256_file(acceptance_path),
                },
            }
        ),
        encoding="utf-8",
    )
    baseline = workspace_snapshot(tmp_path)
    baseline_path = artifacts / "baseline.json"
    baseline_path.write_text(json.dumps(baseline), encoding="utf-8")
    work_unit = {
        "id": "TEST-FAIL",
        "baseline_snapshot": "artifacts/baseline.json",
        "allowed_paths": ["tracked.txt", "artifacts/**"],
        "commands": [
            {
                "name": "forced failure",
                "argv": [sys.executable, "-c", "raise SystemExit(3)"],
            }
        ],
    }
    work_unit_path = artifacts / "work-unit.json"
    work_unit_path.write_text(json.dumps(work_unit), encoding="utf-8")
    baseline = workspace_snapshot(tmp_path)
    baseline_path.write_text(json.dumps(baseline), encoding="utf-8")

    receipt = evaluate_work_unit(tmp_path, work_unit_path, artifacts / "receipt.json")
    assert receipt["result"] == "fail"
    assert receipt["status"] == "rejected"
    assert "command failed: forced failure" in receipt["violations"]


def test_successful_gate_stops_at_candidate(tmp_path):
    init_repo(tmp_path)
    control = tmp_path / "control"
    artifacts = tmp_path / "artifacts"
    control.mkdir()
    artifacts.mkdir()
    acceptance_path = control / "acceptance.json"
    acceptance_path.write_text(json.dumps({"reviewer_owned_paths": ["control/**"]}), encoding="utf-8")
    (control / "acceptance.lock.json").write_text(
        json.dumps(
            {
                "algorithm": "sha256",
                "files": {"control/acceptance.json": sha256_file(acceptance_path)},
            }
        ),
        encoding="utf-8",
    )
    work_unit = {
        "id": "TEST-PASS",
        "baseline_snapshot": "artifacts/baseline.json",
        "allowed_paths": ["tracked.txt", "artifacts/**"],
        "commands": [{"name": "pass", "argv": [sys.executable, "-c", "print('ok')"]}],
    }
    work_unit_path = artifacts / "work-unit.json"
    work_unit_path.write_text(json.dumps(work_unit), encoding="utf-8")
    baseline_path = artifacts / "baseline.json"
    baseline_path.write_text(json.dumps(workspace_snapshot(tmp_path)), encoding="utf-8")
    baseline_path.write_text(json.dumps(workspace_snapshot(tmp_path)), encoding="utf-8")

    receipt = evaluate_work_unit(tmp_path, work_unit_path, artifacts / "receipt.json")
    assert receipt["result"] == "pass"
    assert receipt["status"] == "candidate"
    assert receipt["review"]["status"] == "pending"
