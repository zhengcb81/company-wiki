"""Phase 11 writer-freeze contracts.

These tests intentionally exercise the real script launcher.  They must never
set the legacy authorization pair for a blocked-path test.
"""

from __future__ import annotations

import os
import ast
import re
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from gate_runner import _sanitized_environment, production_data_snapshot
from writer_policy import (
    BLOCKED_EXIT_CODE,
    CONTROL_TOOL_ALLOWLIST,
    legacy_writer_authorized,
)


def _blocked_environment() -> dict[str, str]:
    environment = os.environ.copy()
    for key in list(environment):
        if key.upper().endswith("_API_KEY"):
            environment.pop(key, None)
    environment["COMPANY_WIKI_WRITE_MODE"] = "off"
    environment["COMPANY_WIKI_LEGACY_WRITERS"] = "deny"
    environment["COMPANY_WIKI_REAL_LLM"] = "0"
    environment["COMPANY_WIKI_NETWORK"] = "blocked"
    return environment


@pytest.mark.parametrize(
    ("write_mode", "legacy_switch", "expected"),
    [
        (None, None, False),
        ("off", "allow", False),
        ("legacy", "deny", False),
        ("legacy", "allow", True),
        ("LEGACY", "ALLOW", True),
    ],
)
def test_legacy_authorization_requires_two_explicit_factors(
    write_mode: str | None, legacy_switch: str | None, expected: bool
) -> None:
    environment: dict[str, str] = {}
    if write_mode is not None:
        environment["COMPANY_WIKI_WRITE_MODE"] = write_mode
    if legacy_switch is not None:
        environment["COMPANY_WIKI_LEGACY_WRITERS"] = legacy_switch
    assert legacy_writer_authorized(environment) is expected


def test_gate_environment_cannot_inherit_legacy_authorization(monkeypatch) -> None:
    monkeypatch.setenv("COMPANY_WIKI_WRITE_MODE", "legacy")
    monkeypatch.setenv("COMPANY_WIKI_LEGACY_WRITERS", "allow")
    environment = _sanitized_environment()
    assert environment["COMPANY_WIKI_WRITE_MODE"] == "off"
    assert environment["COMPANY_WIKI_LEGACY_WRITERS"] == "deny"


def test_real_ingest_cli_is_blocked_before_argument_handling() -> None:
    completed = subprocess.run(
        [sys.executable, str(SCRIPTS / "ingest_v2.py"), "--help"],
        cwd=ROOT,
        env=_blocked_environment(),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=20,
        check=False,
    )
    assert completed.returncode == BLOCKED_EXIT_CODE
    assert "LEGACY WRITER BLOCKED" in completed.stdout


def test_explicit_guard_blocks_a_legacy_maintenance_writer() -> None:
    completed = subprocess.run(
        [sys.executable, str(SCRIPTS / "fix_sources_count.py"), "--help"],
        cwd=ROOT,
        env=_blocked_environment(),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=20,
        check=False,
    )
    assert completed.returncode == BLOCKED_EXIT_CODE
    assert "LEGACY WRITER BLOCKED" in completed.stdout


def test_every_direct_writer_cli_has_an_explicit_guard() -> None:
    writer_pattern = re.compile(r"\.write_text\s*\(|\.unlink\s*\(|os\.replace\s*\(")
    explicit_orchestrators = {"scheduler.py", "full_pipeline.py", "batch_ingest.py"}
    missing: list[str] = []
    guarded: list[str] = []
    for path in sorted(SCRIPTS.glob("*.py")):
        if path.name in CONTROL_TOOL_ALLOWLIST:
            continue
        source = path.read_text(encoding="utf-8-sig")
        tree = ast.parse(source)
        has_direct_cli = any(
            isinstance(node, ast.If)
            and "__name__" in ast.unparse(node.test)
            and "__main__" in ast.unparse(node.test)
            for node in tree.body
        )
        is_writer = writer_pattern.search(source) is not None
        if has_direct_cli and (is_writer or path.name in explicit_orchestrators):
            if "enforce_direct_cli" not in source:
                missing.append(path.name)
            else:
                guarded.append(path.name)
    assert not missing, f"direct writer CLIs without fail-closed guard: {missing}"
    assert len(guarded) >= 49, "writer inventory unexpectedly shrank; inspect the scanner"


@pytest.mark.parametrize("script_name", ["ingest_v2.py", "scheduler.py"])
def test_critical_guard_survives_python_no_site_mode(script_name: str) -> None:
    completed = subprocess.run(
        [sys.executable, "-S", str(SCRIPTS / script_name), "--help"],
        cwd=ROOT,
        env=_blocked_environment(),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=20,
        check=False,
    )
    assert completed.returncode == BLOCKED_EXIT_CODE
    assert "LEGACY WRITER BLOCKED" in completed.stdout


def test_control_gate_cli_remains_available() -> None:
    assert "gate_runner.py" in CONTROL_TOOL_ALLOWLIST
    completed = subprocess.run(
        [sys.executable, str(SCRIPTS / "gate_runner.py"), "--help"],
        cwd=ROOT,
        env=_blocked_environment(),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=20,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr


def test_production_snapshot_detects_ignored_and_same_stat_content_changes(
    tmp_path: Path,
) -> None:
    raw = tmp_path / "companies" / "样例公司" / "raw" / "source.md"
    raw.parent.mkdir(parents=True)
    raw.write_text("raw", encoding="utf-8")
    wiki = tmp_path / "companies" / "样例公司" / "wiki" / "page.md"
    wiki.parent.mkdir()
    wiki.write_text("alpha", encoding="utf-8")
    state = tmp_path / ".state" / "state.db"
    state.parent.mkdir()
    state.write_bytes(b"state")

    before = production_data_snapshot(tmp_path)
    original_stat = wiki.stat()
    wiki.write_text("bravo", encoding="utf-8")
    os.utime(wiki, ns=(original_stat.st_atime_ns, original_stat.st_mtime_ns))
    after_rewrite = production_data_snapshot(tmp_path)
    assert after_rewrite["digest"] != before["digest"]

    extra = tmp_path / "sectors" / "行业" / "raw" / "new.pdf"
    extra.parent.mkdir(parents=True)
    extra.write_bytes(b"pdf")
    after_add = production_data_snapshot(tmp_path)
    assert after_add["digest"] != after_rewrite["digest"]
