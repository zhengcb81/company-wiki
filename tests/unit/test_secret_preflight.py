"""Staged-content secret preflight contracts."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from secret_audit import scan_staged


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "tests@example.invalid")
    _git(repo, "config", "user.name", "Tests")
    (repo / "README.md").write_text("safe\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "baseline")
    return repo


def test_staged_real_secret_is_rejected_and_redacted(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    secret = "sk-live-secret-material-1234567890"
    (repo / "config.env").write_text(f"DEEPSEEK_API_KEY={secret}\n", encoding="utf-8")
    _git(repo, "add", "config.env")
    findings = scan_staged(repo)
    assert len(findings) == 1
    assert findings[0]["classification"] == "active_candidate"
    assert secret not in str(findings)


def test_staged_placeholder_is_allowed(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    (repo / ".env.example").write_text(
        "DEEPSEEK_API_KEY=your-key-here\n", encoding="utf-8"
    )
    _git(repo, "add", ".env.example")
    assert [
        item for item in scan_staged(repo) if item["classification"] == "active_candidate"
    ] == []


def test_unstaged_secret_is_outside_precommit_scope(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    (repo / "local.env").write_text(
        "TAVILY_API_KEY=tvly-live-secret-material-1234567890\n", encoding="utf-8"
    )
    assert scan_staged(repo) == []

