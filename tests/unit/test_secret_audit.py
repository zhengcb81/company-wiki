"""Security contracts for redacted working-tree and Git-history secret audits."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from secret_audit import build_audit, sanitize_claude_settings, scan_text, verify_audit


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "tests@example.invalid")
    _git(repo, "config", "user.name", "Tests")
    return repo


def test_scan_text_redacts_secret_and_recognizes_placeholder() -> None:
    real = "sk-live-secret-material-1234567890"
    findings = scan_text(
        f'DEEPSEEK_API_KEY="{real}"\nOPENAI_API_KEY=sk-test-placeholder-123456\n',
        "config.env",
        "working_tree",
    )
    serialized = json.dumps(findings, ensure_ascii=False)
    assert real not in serialized
    assert findings[0]["classification"] == "active_candidate"
    assert findings[1]["classification"] == "placeholder"
    assert all("value" not in finding for finding in findings)


def test_scan_text_detects_new_provider_yaml_keys_and_mimo_token_prefix() -> None:
    minimax = "minimax-live-secret-material-1234567890"
    mimo = "tp-live-secret-material-1234567890"
    findings = scan_text(
        f"minimax_api_key: {minimax}\nmimo_api_key: {mimo}\n",
        "config.yaml",
        "working_tree",
    )
    serialized = json.dumps(findings, ensure_ascii=False)
    assert minimax not in serialized
    assert mimo not in serialized
    assert {finding["kind"] for finding in findings} >= {
        "MINIMAX_API_KEY",
        "MIMO_API_KEY",
    }
    assert all(finding["classification"] == "active_candidate" for finding in findings)


def test_history_secret_is_detected_after_worktree_removal(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    secret = "tvly-live-secret-material-1234567890"
    tracked = repo / "config.txt"
    tracked.write_text(f"TAVILY_API_KEY={secret}\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "add secret")
    tracked.write_text("TAVILY_API_KEY=your-key-here\n", encoding="utf-8")
    _git(repo, "commit", "-qam", "redact secret")

    audit = build_audit(repo, local_env_path=None)
    serialized = json.dumps(audit, ensure_ascii=False)
    assert secret not in serialized
    assert audit["summary"]["history_active_candidates"] >= 1
    assert audit["decision"]["history_rewrite"] == "required_if_blob_was_published"
    assert audit["result"] == "blocked_external"


def test_ignored_local_env_requires_rotation_but_is_not_repo_exposure(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    (repo / ".gitignore").write_text(".env\n", encoding="utf-8")
    (repo / ".env.example").write_text("DEEPSEEK_API_KEY=your-key-here\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "safe baseline")
    secret = "sk-local-secret-material-1234567890"
    (repo / ".env").write_text(f"DEEPSEEK_API_KEY={secret}\n", encoding="utf-8")

    audit = build_audit(repo, local_env_path=repo / ".env")
    serialized = json.dumps(audit, ensure_ascii=False)
    assert secret not in serialized
    assert audit["summary"]["tracked_active_candidates"] == 0
    assert audit["summary"]["local_env_active_candidates"] == 1
    assert audit["decision"]["provider_rotation"] == "external_action_pending"
    assert audit["decision"]["history_rewrite"] == "not_indicated"


def test_sanitize_claude_settings_removes_embedded_secret_without_exposing_it(
    tmp_path: Path,
) -> None:
    secret = "sk-live-secret-material-1234567890"
    path = tmp_path / "settings.local.json"
    path.write_text(
        json.dumps(
            {
                "permissions": {
                    "allow": [
                        "Bash(python:*)",
                        f"Bash(DEEPSEEK_API_KEY={secret} python:*)",
                    ]
                }
            }
        ),
        encoding="utf-8",
    )
    assert sanitize_claude_settings(path) == 1
    content = path.read_text(encoding="utf-8")
    assert secret not in content
    assert "Bash(python:*)" in content


def test_remote_ref_upgrades_history_rewrite_to_required(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    secret = "tvly-live-secret-material-1234567890"
    path = repo / "config.txt"
    path.write_text(f"TAVILY_API_KEY={secret}\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "secret")
    _git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
    audit = build_audit(repo, local_env_path=None)
    assert audit["decision"]["history_rewrite"] == "required_authorization_pending"
    assert audit["decision"]["remote_refs_support_publication"] == ["origin/main"]


def test_placeholder_line_movement_does_not_invalidate_security_projection(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    path = repo / "notes.md"
    path.write_text("TAVILY_API_KEY=your-key-here\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "placeholder")
    audit = build_audit(repo, local_env_path=None)
    path.write_text("\nTAVILY_API_KEY=your-key-here\n", encoding="utf-8")
    assert verify_audit(repo, audit, local_env_path=None) == []
