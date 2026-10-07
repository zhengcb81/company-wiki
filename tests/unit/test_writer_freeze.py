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
sys.path.insert(0, str(ROOT / "tests"))

from helpers.fixture_files import snapshot_files
from writer_policy import (
    BLOCKED_EXIT_CODE,
    CONTROL_TOOL_ALLOWLIST,
    SOURCE_WORKFLOW_TOOL_ALLOWLIST,
    PERMANENTLY_RETIRED_SCRIPTS,
    is_legacy_script_cli,
    legacy_script_execution_allowed,
)


def _blocked_environment() -> dict[str, str]:
    environment = os.environ.copy()
    for key in list(environment):
        if key.upper().endswith("_API_KEY"):
            environment.pop(key, None)
    environment["COMPANY_WIKI_REAL_LLM"] = "0"
    environment["COMPANY_WIKI_NETWORK"] = "blocked"
    # These CLIs import the package from src/ when launched as scripts. Set
    # this explicitly so the test does not inherit pre-push's local PYTHONPATH.
    environment["PYTHONPATH"] = str(ROOT / "src")
    return environment


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


def _has_direct_cli(tree: ast.Module) -> bool:
    return any(
        isinstance(node, ast.If)
        and "__name__" in ast.unparse(node.test)
        and "__main__" in ast.unparse(node.test)
        for node in tree.body
    )


def test_every_direct_writer_cli_has_an_explicit_guard() -> None:
    writer_pattern = re.compile(r"\.write_text\s*\(|\.unlink\s*\(|os\.replace\s*\(")
    explicit_orchestrators = {"scheduler.py", "batch_ingest.py"}
    missing: list[str] = []
    for path in sorted(SCRIPTS.glob("*.py")):
        if path.name in CONTROL_TOOL_ALLOWLIST | SOURCE_WORKFLOW_TOOL_ALLOWLIST:
            continue
        source = path.read_text(encoding="utf-8-sig")
        tree = ast.parse(source)
        is_writer = writer_pattern.search(source) is not None
        if _has_direct_cli(tree) and (is_writer or path.name in explicit_orchestrators):
            if "enforce_direct_cli" not in source:
                missing.append(path.name)
    assert not missing, f"direct writer CLIs without fail-closed guard: {missing}"


def test_direct_writer_clis_are_frozen_or_current_entries() -> None:
    writer_pattern = re.compile(r"\.write_text\s*\(|\.unlink\s*\(|os\.replace\s*\(")
    explicit_orchestrators = {"scheduler.py", "batch_ingest.py"}
    offenders: list[str] = []
    for path in sorted(SCRIPTS.glob("*.py")):
        source = path.read_text(encoding="utf-8-sig")
        tree = ast.parse(source)
        if not _has_direct_cli(tree):
            continue
        name = path.name
        if name in CONTROL_TOOL_ALLOWLIST | SOURCE_WORKFLOW_TOOL_ALLOWLIST:
            if legacy_script_execution_allowed(name) is not True:
                offenders.append(f"{name}: current entry not runnable")
            continue
        is_writer = writer_pattern.search(source) is not None
        if not is_writer and name not in explicit_orchestrators:
            continue
        if legacy_script_execution_allowed(name) is not False:
            offenders.append(f"{name}: writer entry not frozen")
        elif "enforce_direct_cli" not in source:
            offenders.append(f"{name}: frozen entry without explicit guard")
    assert not offenders, offenders


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


@pytest.mark.parametrize(
    "script_name",
    [
        "narrative_evidence_pilot.py",
        "narrative_summary_review_pilot.py",
    ],
)
def test_source_workflow_cli_is_not_a_legacy_research_writer(script_name: str) -> None:
    assert not is_legacy_script_cli(SCRIPTS / script_name)
    completed = subprocess.run(
        [sys.executable, str(SCRIPTS / script_name), "--help"],
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
    assert "LEGACY WRITER BLOCKED" not in completed.stdout


def test_source_workflow_classification_does_not_reenable_retired_research() -> None:
    assert not SOURCE_WORKFLOW_TOOL_ALLOWLIST & PERMANENTLY_RETIRED_SCRIPTS


def test_fixture_snapshot_detects_ignored_and_same_stat_content_changes(
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

    before = snapshot_files(tmp_path)
    original_stat = wiki.stat()
    wiki.write_text("bravo", encoding="utf-8")
    os.utime(wiki, ns=(original_stat.st_atime_ns, original_stat.st_mtime_ns))
    after_rewrite = snapshot_files(tmp_path)
    assert after_rewrite != before

    # The original-file fixture is protected by content as well, even when
    # a writer restores both its size and modification timestamp.
    raw_stat = raw.stat()
    raw.write_text("RAW", encoding="utf-8")
    os.utime(raw, ns=(raw_stat.st_atime_ns, raw_stat.st_mtime_ns))
    after_raw_rewrite = snapshot_files(tmp_path)
    assert after_raw_rewrite != after_rewrite

    extra = tmp_path / "sectors" / "行业" / "raw" / "new.pdf"
    extra.parent.mkdir(parents=True)
    extra.write_bytes(b"pdf")
    after_add = snapshot_files(tmp_path)
    assert after_add != after_raw_rewrite
