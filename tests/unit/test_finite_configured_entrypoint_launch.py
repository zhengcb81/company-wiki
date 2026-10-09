"""Launch the finite configured source entry with real interpreter startup hooks."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"


def _launch(script_name, args, cwd, *, old_permission_pair=False):
    env = dict(os.environ)
    for name in list(env):
        if name.upper().endswith("_API_KEY"):
            env.pop(name)
    # Both directories are required by the real configured invocation:
    # src provides the finite pipeline, scripts provides Config and sitecustomize.
    env.update(PYTHONPATH=os.pathsep.join((str(ROOT / "src"), str(SCRIPTS))),
               PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1",
               PYTHON_DOTENV_DISABLED="1", WIKI_ROOT=str(cwd))
    env.pop("COMPANY_WIKI_WRITE_MODE", None)
    env.pop("COMPANY_WIKI_LEGACY_WRITERS", None)
    if old_permission_pair:
        env.update(COMPANY_WIKI_WRITE_MODE="legacy", COMPANY_WIKI_LEGACY_WRITERS="allow")
    return subprocess.run([sys.executable, "-B", str(SCRIPTS / script_name), *args],
                          cwd=cwd, env=env, capture_output=True, text=True,
                          encoding="utf-8", timeout=20, check=False)


@pytest.mark.parametrize("flag", ["--help", "-h"])
def test_finite_configured_help_runs_with_script_startup_policy_active(tmp_path, flag):
    sentinel = tmp_path / "keep.txt"
    sentinel.write_bytes(b"original fixture")
    before = {path.name: path.read_bytes() for path in tmp_path.iterdir()}
    result = _launch("narrative_batch_configured.py", [flag], tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "LEGACY WRITER BLOCKED" not in result.stdout + result.stderr
    assert "--llm-config" in result.stdout and "--llm-provider" in result.stdout
    assert "--request" in result.stdout and "--catalog-config" in result.stdout
    assert {path.name: path.read_bytes() for path in tmp_path.iterdir()} == before


@pytest.mark.parametrize("script_name,marker", [
    ("ingest_v2.py", "LEGACY WRITER BLOCKED - PERMANENTLY RETIRED"),
    ("semantic_gate.py", "LEGACY_ENGINEERING_TOOL_RETIRED"),
    ("collect_reports.py", "LEGACY WRITER BLOCKED: collect_reports.py"),
])
@pytest.mark.parametrize("old_permission_pair", [False, True])
def test_research_retired_engineering_and_mixed_entries_stay_frozen(
    tmp_path, script_name, marker, old_permission_pair,
):
    sentinel = tmp_path / "keep.txt"
    sentinel.write_bytes(b"original fixture")
    before = {path.name: path.read_bytes() for path in tmp_path.iterdir()}
    result = _launch(script_name, ["--help"], tmp_path,
                     old_permission_pair=old_permission_pair)
    assert result.returncode == 78, result.stdout + result.stderr
    assert marker in result.stdout
    assert {path.name: path.read_bytes() for path in tmp_path.iterdir()} == before
