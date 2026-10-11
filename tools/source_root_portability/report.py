"""Run-report assembly for schema cwp-root-portability/1."""

from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "cwp-root-portability/1"
MAX_REPORT_BYTES = 8 * 1024 * 1024

# Modules whose actual bytes decide read behavior; recorded every run.
TRACKED_MODULES = (
    "src/company_wiki/source_catalog/source_reader.py",
    "src/company_wiki/source_catalog/config.py",
    "src/company_wiki/source_catalog/service.py",
    "src/company_wiki/source_catalog/store.py",
    "src/company_wiki/source_catalog/scanner.py",
    "src/company_wiki/source_catalog/resolver.py",
    "src/company_wiki/source_catalog/document_kinds.py",
    "src/company_wiki/source_contract/source_export_v2.py",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 16), b""):
            digest.update(chunk)
    return digest.hexdigest()


def capture_code_identity(worktree_root: Path) -> dict[str, Any]:
    """Actual HEAD, module files/SHA and the company_wiki import binding."""

    def git(*args: str) -> str:
        try:
            completed = subprocess.run(
                ["git", *args], cwd=worktree_root, capture_output=True,
                text=True, timeout=30, check=False,
            )
        except (OSError, subprocess.SubprocessError):
            return "unavailable"
        return completed.stdout.strip() if completed.returncode == 0 else "unavailable"

    modules = []
    for relative in TRACKED_MODULES:
        path = worktree_root / relative
        modules.append({
            "path": relative,
            "sha256": sha256_file(path) if path.is_file() else "missing",
            "source": "worktree",
        })
    try:
        import company_wiki

        company_wiki_file = str(Path(company_wiki.__file__).resolve())
    except Exception:  # noqa: BLE001 - identity recording must not raise
        company_wiki_file = "unavailable"
    return {
        "head": git("rev-parse", "HEAD"),
        "branch": git("branch", "--show-current"),
        "modules": modules,
        "python_binding": {
            "company_wiki_file": company_wiki_file.replace("\\", "/"),
            "bound_root": str(worktree_root / "src").replace("\\", "/"),
        },
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
