"""Cross-repo read-only proof (card section 6, last bullet / section 8).

The session snapshots ``HEAD`` + ``git status --porcelain`` of this worktree, a
digest of this card's ``fixtures/`` tree, and the same two facts for every
consumer repository the environment provides.  The read-only test re-reads all
of them and asserts nothing changed; ``sessionreport.finalize`` re-checks at
session finish so a write after the last test still fails the run.  A missing
snapshot is a failure, never a silent pass.
"""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path
from typing import Any

from . import constants as C
from . import environment as E


_BASELINE: dict[str, Any] | None = None


def _git(root: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(root), *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=60,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)} failed in {root}: "
            f"{proc.stderr.decode('utf-8', 'replace')[:200]}"
        )
    return proc.stdout.decode("utf-8", "replace")


def repo_state() -> dict[str, str]:
    """``HEAD`` plus porcelain status of the worktree under test."""
    return {
        "head": _git(C.REPO_ROOT, "rev-parse", "HEAD").strip(),
        "status": _git(C.REPO_ROOT, "status", "--porcelain"),
    }


def consumer_snapshots() -> dict[str, dict[str, str]]:
    """``HEAD`` + porcelain for every env-provided consumer repo root."""
    snapshots: dict[str, dict[str, str]] = {}
    for name in C.CONSUMERS:
        root = E.consumer_root(name)
        if root is not None and root.is_dir():
            snapshots[name] = {
                "root": str(root),
                "head": _git(root, "rev-parse", "HEAD").strip(),
                "status": _git(root, "status", "--porcelain"),
            }
    return snapshots


def tree_digest(root: Path) -> str:
    """Order-independent digest over every file below ``root`` (path + bytes)."""
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        digest.update(str(path.relative_to(root)).replace("\\", "/").encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def capture_baseline() -> dict[str, Any]:
    """Snapshot repo, fixtures tree and consumer repos; once, at session start."""
    global _BASELINE
    _BASELINE = {
        **repo_state(),
        "fixtures_digest": tree_digest(C.FIXTURES_DIR),
        "consumers": consumer_snapshots(),
    }
    return _BASELINE


def baseline() -> dict[str, Any] | None:
    return _BASELINE


def current() -> dict[str, Any]:
    return {
        **repo_state(),
        "fixtures_digest": tree_digest(C.FIXTURES_DIR),
        "consumers": consumer_snapshots(),
    }


def diff(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    """Names of everything that changed between two snapshots."""
    changed: list[str] = []
    if before["head"] != after["head"]:
        changed.append("HEAD")
    if before["status"] != after["status"]:
        changed.append("git status --porcelain (worktree)")
    if before["fixtures_digest"] != after["fixtures_digest"]:
        changed.append("fixtures/ tree digest")
    for name, after_state in after.get("consumers", {}).items():
        before_state = before.get("consumers", {}).get(name)
        if before_state is None:
            continue
        if before_state["head"] != after_state["head"]:
            changed.append(f"consumer {name} HEAD")
        if before_state["status"] != after_state["status"]:
            changed.append(f"consumer {name} git status --porcelain")
    return {
        "changed": changed,
        "before_status": before["status"],
        "after_status": after["status"],
        "consumer_roots": sorted(after.get("consumers", {})),
    }


def verify_unchanged() -> list[str]:
    """Re-check the session baseline at finish; empty means still read-only."""
    if _BASELINE is None:
        raise RuntimeError("no session baseline was captured")
    return diff(_BASELINE, current())["changed"]
