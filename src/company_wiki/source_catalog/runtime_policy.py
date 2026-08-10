"""FC-201: persistent, versioned RuntimePolicySnapshot (ActivationSnapshot 1.0).

The snapshot is the single activation authority (ADR-010): it carries the
v2 flag set, the current activation epoch, the active cohorts, and the
RootPolicy hash.  Request start pins the snapshot; the flag set alone can
hide active rows even when the database contains them; reads fail closed
(missing / corrupt / unknown flag / illegal dependency / placeholder hash
are all errors, never silent defaults); writes are compare-and-swap so a
stale writer can never clobber a concurrent activation flip.

This module replaces the hardcoded flag dicts in WU scripts (FC-201
deletion deadline per ADR-010).  Resolver SQL enforcement lands in FC-202.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from .flags import FLAGS, validate_flag_state

RUNTIME_POLICY_SCHEMA_VERSION = "1.0"
_HEX = set("0123456789abcdef")


class RuntimePolicyError(ValueError):
    """Raised when the runtime policy snapshot is missing, corrupt, or invalid."""


def snapshot_hash(snapshot: dict[str, Any]) -> str:
    """Canonical sha256 of the snapshot payload, excluding its own hash field."""
    without_hash = {k: v for k, v in snapshot.items() if k != "snapshot_sha256"}
    payload = json.dumps(without_hash, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def validate_snapshot(snapshot: dict[str, Any]) -> list[str]:
    """Return structural + semantic problems ([] = valid)."""
    problems: list[str] = []
    if not isinstance(snapshot, dict):
        return ["snapshot must be an object"]
    if snapshot.get("schema_version") != RUNTIME_POLICY_SCHEMA_VERSION:
        problems.append(
            f"schema_version must be {RUNTIME_POLICY_SCHEMA_VERSION!r} "
            f"(got {snapshot.get('schema_version')!r})"
        )
    flags = snapshot.get("flags")
    if not isinstance(flags, dict):
        problems.append("flags must be an object")
    else:
        missing = set(FLAGS) - set(flags)
        unknown = set(flags) - set(FLAGS)
        if missing:
            problems.append(f"flags missing: {sorted(missing)}")
        if unknown:
            problems.append(f"flags unknown: {sorted(unknown)}")
        if not all(isinstance(v, bool) for v in flags.values()):
            problems.append("flags values must be booleans")
        if not missing and not unknown:
            problems += validate_flag_state(flags)

    policy_hash = snapshot.get("policy_hash")
    if not (
        isinstance(policy_hash, str)
        and len(policy_hash) == 64
        and all(c in _HEX for c in policy_hash.lower())
    ):
        problems.append("policy_hash must be a 64-char hex sha256")

    epoch = snapshot.get("current_epoch")
    if epoch is not None and not (
        isinstance(epoch, str) and epoch.strip()
    ):
        problems.append("current_epoch must be None or non-empty text")

    cohorts = snapshot.get("active_cohorts")
    if not isinstance(cohorts, list) or not all(
        isinstance(c, str) and c.strip() for c in cohorts
    ):
        problems.append("active_cohorts must be a list of non-empty strings")

    updated_at = snapshot.get("updated_at")
    if not (isinstance(updated_at, str) and updated_at.strip()):
        problems.append("updated_at must be non-empty text")
    return problems


def build_snapshot(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate a payload and return a snapshot with its canonical hash."""
    problems = validate_snapshot(payload)
    if problems:
        raise RuntimePolicyError("; ".join(problems))
    snapshot = dict(payload)
    snapshot["snapshot_sha256"] = snapshot_hash(snapshot)
    return snapshot


def load_runtime_policy(path: Path) -> dict[str, Any]:
    """Fail-closed load: missing/corrupt/invalid snapshot raises.

    Returns a fresh dict each call, so a request that pinned the snapshot
    keeps its own copy even when the file changes mid-request (CTRL-05).
    """
    try:
        raw = Path(path).read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise RuntimePolicyError(
            f"no runtime policy snapshot at {path} (fail closed)"
        ) from exc
    except OSError as exc:
        raise RuntimePolicyError(
            f"cannot read runtime policy snapshot at {path}: {exc}"
        ) from exc
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimePolicyError(
            f"runtime policy snapshot at {path} is corrupt: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise RuntimePolicyError(
            f"runtime policy snapshot at {path} must be an object"
        )
    problems = validate_snapshot(payload)
    if problems:
        raise RuntimePolicyError(
            f"runtime policy snapshot at {path} invalid: {'; '.join(problems)}"
        )
    declared = payload.get("snapshot_sha256")
    computed = snapshot_hash(payload)
    if declared != computed:
        raise RuntimePolicyError(
            f"runtime policy snapshot at {path} hash mismatch: "
            f"declared {declared!r} != computed {computed[:12]}..."
        )
    return dict(payload)


def _atomic_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(
        dir=str(path.parent), prefix=path.name, suffix=".tmp"
    )
    temporary = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, ensure_ascii=False, sort_keys=True)
            handle.write("\n")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def save_runtime_policy_cas(
    path: Path,
    snapshot: dict[str, Any],
    *,
    expected_hash: str | None,
) -> str:
    """Compare-and-swap write.

    ``expected_hash=None`` requires the file to NOT exist (first write);
    otherwise the current file's hash must equal ``expected_hash``.  On
    mismatch the write is refused and the file is left untouched (a stale
    writer can never clobber a concurrent activation flip).
    """
    target = Path(path)
    if expected_hash is None:
        if target.exists():
            raise RuntimePolicyError(
                f"CAS first-write refused: {target} already exists"
            )
    else:
        current = load_runtime_policy(target)
        current_hash = current["snapshot_sha256"]
        if current_hash != expected_hash:
            raise RuntimePolicyError(
                f"CAS conflict: current snapshot hash {current_hash[:12]}... "
                f"!= expected {str(expected_hash)[:12]}... (concurrent change?)"
            )
    built = build_snapshot(snapshot)
    _atomic_write(target, built)
    return built["snapshot_sha256"]


def reader_mode(snapshot: dict[str, Any]) -> str:
    """Return the effective reader: 'v2' only when v2_resolve_active is on."""
    return "v2" if snapshot.get("flags", {}).get("v2_resolve_active") else "v1"


__all__ = [
    "RUNTIME_POLICY_SCHEMA_VERSION",
    "RuntimePolicyError",
    "build_snapshot",
    "load_runtime_policy",
    "reader_mode",
    "save_runtime_policy_cas",
    "snapshot_hash",
    "validate_snapshot",
]
