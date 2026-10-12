"""Run-report assembly for schema ``narrative-g2-replay/1``."""

from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "narrative-g2-replay/1"
MAX_REPORT_BYTES = 8 * 1024 * 1024
MAX_BUNDLE_BYTES = 8 * 1024 * 1024

# Modules whose actual bytes decide the summary -> read -> RF behaviour.
# Recorded every run so a record can be tied to exact code, never to "latest".
TRACKED_MODULES = (
    "src/company_wiki/automation/narrative_batch_cli.py",
    "src/company_wiki/automation/narrative_batch.py",
    "src/company_wiki/automation/narrative_batch_request.py",
    "src/company_wiki/automation/narrative_select.py",
    "src/company_wiki/automation/narrative_summarize.py",
    "src/company_wiki/automation/narrative_verify.py",
    "src/company_wiki/automation/narrative_runtime.py",
    "src/company_wiki/automation/narrative_formats.py",
    "src/company_wiki/automation/narrative_transport_contracts.py",
    "src/company_wiki/source_catalog/narrative_transport_cli.py",
    "src/company_wiki/source_catalog/narrative_evidence.py",
    "src/company_wiki/source_catalog/narrative_normalization.py",
    "src/company_wiki/source_catalog/narrative_business_groups.py",
    "src/company_wiki/source_catalog/narrative_group_candidates.py",
    "src/company_wiki/source_catalog/narrative_stage_assertions.py",
    "src/company_wiki/source_catalog/narrative_budget.py",
    "tools/narrative_g2_replay/run.py",
    "tools/narrative_g2_replay/specs.py",
    "tools/narrative_g2_replay/oracle.py",
    "tools/narrative_g2_replay/observations.py",
)

# The fixed RF code-only snapshot consumed read-only by this package.
RF_SNAPSHOT_MODULES = (
    "scripts/company_wiki_narrative_reader.py",
    "scripts/narrative_source_preparation.py",
    "scripts/company_wiki_narrative_contracts.py",
    "scripts/company_wiki_narrative_process.py",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 16), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _git(worktree_root: Path, *args: str) -> str:
    try:
        completed = subprocess.run(
            ["git", *args], cwd=worktree_root, capture_output=True,
            text=True, timeout=30, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return "unavailable"
    return completed.stdout.strip() if completed.returncode == 0 else "unavailable"


def _modules(worktree_root: Path, relatives) -> list[dict[str, Any]]:
    entries = []
    for relative in relatives:
        path = worktree_root / relative
        entries.append({
            "path": relative,
            "sha256": sha256_file(path) if path.is_file() else "missing",
            "byte_size": path.stat().st_size if path.is_file() else 0,
            "source": "worktree" if path.is_file() else "missing",
        })
    return entries


def capture_code_identity(worktree_root: Path) -> dict[str, Any]:
    """Actual HEAD, module files/SHA and the company_wiki import binding."""
    try:
        import company_wiki

        company_wiki_file = str(Path(company_wiki.__file__).resolve())
    except Exception:  # noqa: BLE001 - identity recording must not raise
        company_wiki_file = "unavailable"
    return {
        "base_head": _git(worktree_root, "rev-parse", "HEAD"),
        "branch": _git(worktree_root, "branch", "--show-current"),
        "modules": _modules(worktree_root, TRACKED_MODULES),
        "python_binding": {
            "company_wiki_file": company_wiki_file.replace("\\", "/"),
            "bound_root": str(worktree_root / "src").replace("\\", "/"),
        },
    }


def capture_rf_snapshot_identity(rf_project: Path) -> dict[str, Any]:
    """The fixed RF code-only snapshot this package consumed read-only."""
    return {
        "project_ref": str(rf_project).replace("\\", "/"),
        "modules": _modules(rf_project, RF_SNAPSHOT_MODULES),
    }


def assert_worktree_binding(worktree_root: Path) -> None:
    """Refuse to run against a different checkout (editable-install fallback)."""
    import company_wiki

    bound = Path(company_wiki.__file__).resolve()
    expected = (worktree_root / "src" / "company_wiki").resolve()
    if expected not in bound.parents and bound.parent != expected:
        raise RuntimeError(
            f"company_wiki imported from {bound}, expected {expected}; "
            "bind PYTHONPATH to the worktree src first"
        )


@dataclass
class AttemptDir:
    """A fresh attempt directory under the out root; never overwrites attempts."""

    path: Path
    attempt_id: str


def create_attempt(out_root: Path) -> AttemptDir:
    out_root = Path(out_root)
    out_root.mkdir(parents=True, exist_ok=True)
    index = 1
    while True:
        attempt_id = f"attempt-{index:04d}"
        path = out_root / attempt_id
        try:
            path.mkdir(exist_ok=False)
            return AttemptDir(path=path, attempt_id=attempt_id)
        except FileExistsError:
            index += 1


def write_report(attempt: AttemptDir, report: dict[str, Any]) -> Path:
    payload = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=False)
    path = attempt.path / "report.json"
    data = payload.encode("utf-8")
    if len(data) > MAX_REPORT_BYTES:
        raise RuntimeError(
            f"report exceeds {MAX_REPORT_BYTES} bytes ({len(data)}); "
            "the persistent report must stay small"
        )
    path.write_bytes(data)
    return path
