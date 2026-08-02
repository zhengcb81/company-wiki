"""Contracts for the Phase 11 tracked-deletion manifest."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from deletion_manifest import build_manifest, verify_manifest, write_manifest


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "tests@example.invalid")
    _git(repo, "config", "user.name", "Tests")
    files = {
        "companies/示例公司/extracts/report.md": "extract\n",
        "companies/示例公司/wiki/公司动态.md": "wiki\n",
        "companies/示例公司/wiki/archive/旧页.md": "archive\n",
        "keep.md": "keep\n",
    }
    for relative, content in files.items():
        path = repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "fixture")
    (repo / "companies/示例公司/extracts/report.md").unlink()
    (repo / "companies/示例公司/wiki/公司动态.md").unlink()
    (repo / "companies/示例公司/wiki/archive/旧页.md").unlink()
    return repo


def test_build_manifest_is_complete_restorable_and_classified(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    manifest = build_manifest(repo, backup_id="fixture-backup")

    assert manifest["summary"]["total"] == 3
    assert manifest["summary"]["categories"] == {
        "company_wiki": 1,
        "derived_extract": 1,
        "wiki_archive": 1,
    }
    assert manifest["policy"]["commit_blocked"] is True
    assert manifest["policy"]["decision_state"] == "user_authorized_derived_cleanup"
    assert manifest["policy"]["user_authorized"] is True
    assert manifest["policy"]["independent_review_required"] is True
    assert manifest["policy"]["original_source_entries"] == 0
    assert all(entry["head_blob_oid"] for entry in manifest["entries"])
    assert all(len(entry["content_sha256"]) == 64 for entry in manifest["entries"])
    assert all(entry["recovery"]["git_head"] for entry in manifest["entries"])
    assert verify_manifest(repo, manifest) == []


def test_verify_rejects_workspace_drift(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    manifest = build_manifest(repo)
    _git(
        repo,
        "restore",
        "--source=HEAD",
        "--worktree",
        "--",
        "companies/示例公司/wiki/公司动态.md",
    )
    violations = verify_manifest(repo, manifest)
    assert any("deleted path set differs" in item for item in violations)


def test_verify_rejects_manifest_tampering(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    manifest = build_manifest(repo)
    manifest["entries"][0]["category"] = "other"
    violations = verify_manifest(repo, manifest)
    assert any("manifest digest mismatch" in item for item in violations)
    assert any("category mismatch" in item for item in violations)


def test_verify_rejects_staged_deletions(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    manifest = build_manifest(repo)
    _git(repo, "add", "-u")
    violations = verify_manifest(repo, manifest)
    assert any("deletion is staged" in item for item in violations)


def test_written_manifest_round_trips(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    output = tmp_path / "deletion-manifest.json"
    manifest = build_manifest(repo)
    write_manifest(manifest, output)
    loaded = json.loads(output.read_text(encoding="utf-8"))
    assert loaded == manifest
    assert verify_manifest(repo, loaded) == []


def test_build_rejects_original_source_deletion(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    raw = repo / "companies" / "示例公司" / "raw" / "report.pdf"
    raw.parent.mkdir(parents=True, exist_ok=True)
    raw.write_bytes(b"original source fixture")
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "add original source")
    raw.unlink()

    with pytest.raises(ValueError, match="original or unclassified"):
        build_manifest(repo)
