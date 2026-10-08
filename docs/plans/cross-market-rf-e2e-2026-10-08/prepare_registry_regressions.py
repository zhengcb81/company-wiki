"""One-shot isolated regression preparation for the independently reproduced audit bug."""
from pathlib import Path
import shutil

repo = Path("C:/Users/郑曾波/Projects/revenue-forecast")
destination = repo / "tests/test_registry_artifact_audit.py"
assert not destination.exists(), "Do not overwrite an existing owner file"
destination.write_text('''"""Public registry audit must accept registered anchors and reject absent ones."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from publication_registry import audit, register_publication  # noqa: E402


@pytest.fixture
def registered(tmp_path, monkeypatch):
    monkeypatch.setenv("REVENUE_PUBLICATION_REGISTRY", str(tmp_path / "registry.jsonl"))
    result = {
        "input_sha256": "a" * 64, "result_sha256": "b" * 64,
        "engine_version": "4.1.0", "schema_version": "3.7",
        "company_name": "Audit fixture", "as_of_date": "2026-10-08",
        "forecast_version": "fixture-v1",
    }
    register_publication(result)
    artifact = tmp_path / "forecast.json"
    artifact.write_text(json.dumps(result), encoding="utf-8")
    return result, artifact


def test_registered_result_is_not_an_unregistered_claim(registered):
    _, artifact = registered
    assert audit([artifact]) == []


def test_cross_version_and_snapshot_history_do_not_hide_registered_anchor(registered):
    result, artifact = registered
    register_publication({**result, "engine_version": "4.2.0", "result_sha256": "c" * 64})
    register_publication(result, artifact_type="snapshot")
    assert audit([artifact]) == []


def test_missing_anchor_still_fails(registered):
    result, artifact = registered
    artifact.write_text(json.dumps({**result, "input_sha256": "d" * 64}), encoding="utf-8")
    assert any("unregistered claim" in item for item in audit([artifact]))


def test_same_generation_conflict_still_fails(registered):
    result, artifact = registered
    register_publication({**result, "result_sha256": "e" * 64})
    assert any("conflict" in item for item in audit([artifact]))


def test_since_filter_applies_to_registered_anchor_check(registered):
    _, artifact = registered
    assert any("unregistered claim" in item for item in audit([artifact], since="9999"))


@pytest.mark.parametrize("known,expected_code", [(True, 0), (False, 1)])
def test_real_cli_reports_correct_exit_status(registered, known, expected_code):
    result, artifact = registered
    if not known:
        artifact.write_text(json.dumps({**result, "input_sha256": "f" * 64}), encoding="utf-8")
    cli = Path(__file__).resolve().parents[1] / "scripts/publication_registry.py"
    completed = subprocess.run(
        [sys.executable, "-B", str(cli), "audit", "--result", str(artifact)],
        env=os.environ.copy(), capture_output=True, text=True, check=False,
    )
    assert completed.returncode == expected_code, completed.stdout + completed.stderr
    assert ("unregistered claim" in completed.stdout) == (not known)
''', encoding="utf-8")
print(destination)
