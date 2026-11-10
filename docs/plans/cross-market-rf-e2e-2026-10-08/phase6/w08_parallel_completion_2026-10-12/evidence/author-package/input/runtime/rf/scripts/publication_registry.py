"""Append-only publication registry (R1.2, roadmap RC-1 / N-01).

The registry is the artifact-external authority that records which input
anchors were actually published by ``run_forecast``.  It turns ``input_sha256``
from a self-reported anchor into an externally queryable fact: a consumer can
ask "was this input ever published, and to which results?" and a forged
artifact anchored to an unpublished (or misregistered) input is rejected.

Structure: append-only JSONL, one entry per line, chained line hashes
(``prev_line_sha256`` -> ``line_sha256``) so any mid-file tampering breaks the
chain and is detected by ``lookup``/``audit``/``_read_entries``.  Writes are
fsync'd; after each append the file is set read-only (best-effort, as an
accidental-overwrite guard — the chain hash is the actual integrity gate).
"""

from __future__ import annotations

import argparse
import json
import os
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from contracts.evidence import canonical_sha256

REGISTRY_FILE = "publications.jsonl"
ENV_REGISTRY = "REVENUE_PUBLICATION_REGISTRY"
DEFAULT_PUBLISHER = "revenue-forecast"


class RegistryError(RuntimeError):
    """Raised when the registry is missing, corrupt, or unavailable."""


def registry_file() -> Path:
    """Resolve the registry path: env override (file or directory), else repo default."""
    env = os.environ.get(ENV_REGISTRY)
    if env:
        path = Path(env).expanduser()
        if path.is_dir():
            return path / REGISTRY_FILE
        return path
    return Path(__file__).resolve().parents[1] / "artifacts" / "registry" / REGISTRY_FILE


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_entries() -> list[dict[str, Any]]:
    """Read and verify every line (hash + chain).  Corrupt line -> RegistryError."""
    path = registry_file()
    if not path.exists():
        return []
    entries: list[dict[str, Any]] = []
    previous: str | None = None
    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw.strip():
            continue
        try:
            entry = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RegistryError(f"registry line {lineno}: invalid JSON: {exc}") from exc
        claimed = entry.get("line_sha256")
        payload = {key: value for key, value in entry.items() if key != "line_sha256"}
        if canonical_sha256(payload) != claimed:
            raise RegistryError(f"registry line {lineno}: hash mismatch (tampered)")
        if entry.get("prev_line_sha256") != previous:
            raise RegistryError(
                f"registry line {lineno}: chain break (prev_line_sha256 mismatch)"
            )
        previous = claimed
        entries.append(entry)
    return entries


def _set_read_only(path: Path) -> None:
    """Best-effort accidental-overwrite guard (the chain hash is the real gate)."""
    try:
        path.chmod(stat.S_IREAD)
    except OSError:
        pass


def _clear_read_only(path: Path) -> None:
    try:
        path.chmod(stat.S_IWRITE | stat.S_IREAD)
    except OSError:
        pass


def _append(entry: dict[str, Any]) -> None:
    """Append one entry with a chained line hash; fail closed on any problem."""
    path = registry_file()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise RegistryError(f"publication registry unavailable: {exc}") from exc
    # Write-precheck: a corrupt or unverifiable existing registry blocks writes.
    existing = _read_entries()
    payload = {key: value for key, value in entry.items() if key != "line_sha256"}
    payload["prev_line_sha256"] = existing[-1]["line_sha256"] if existing else None
    line = {**payload, "line_sha256": canonical_sha256(payload)}
    if path.exists():
        _clear_read_only(path)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(line, ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    _set_read_only(path)


def input_summary_sha256(result: dict[str, Any]) -> str:
    """Hash of the identity fields a human would use to recognize the input."""
    return canonical_sha256(
        {
            "company_name": result.get("company_name"),
            "as_of_date": result.get("as_of_date"),
            "forecast_version": result.get("forecast_version"),
        }
    )


def register_publication(
    result: dict[str, Any],
    *,
    artifact_type: str = "forecast",
    artifact_id: str | None = None,
    note: str = "run_forecast formal",
    validation_status: str = "validated",
) -> None:
    """Register a published artifact's anchor.  Raises RegistryError on failure.

    ZR-701: *validation_status* distinguishes explicit Draft artifacts
    (``"draft"`` — computed but not strong-validated; the entry carries no
    validated receipt anchor) from Formal artifacts (``"validated"`` —
    strong-validated publication).  The key is additive: pre-ZR-701 lines
    simply lack it and stay readable.
    """
    receipt = result.get("publication_receipt")
    _append(
        {
            "registered_at": _utc_now_iso(),
            "input_sha256": result["input_sha256"],
            "result_sha256": result["result_sha256"],
            "receipt_sha256": canonical_sha256(receipt) if isinstance(receipt, dict) else None,
            "engine_version": result.get("engine_version"),
            "schema_version": result.get("schema_version"),
            "publisher": os.environ.get("REVENUE_PUBLISHER", DEFAULT_PUBLISHER),
            "input_summary_sha256": input_summary_sha256(result),
            "artifact_type": artifact_type,
            "artifact_id": artifact_id,
            "note": note,
            "validation_status": validation_status,
        }
    )


def register_snapshot(snapshot: dict[str, Any]) -> None:
    """Register a backtest snapshot's anchor (snapshot_id <-> input_sha256)."""
    _append(
        {
            "registered_at": _utc_now_iso(),
            "input_sha256": snapshot["input_sha256"],
            "result_sha256": snapshot["forecast_result_sha256"],
            "receipt_sha256": canonical_sha256(snapshot["forecast_result"].get("publication_receipt"))
            if isinstance(snapshot.get("forecast_result"), dict)
            else None,
            "engine_version": snapshot.get("engine_version"),
            "schema_version": snapshot.get("forecast_schema_version"),
            "publisher": os.environ.get("REVENUE_PUBLISHER", DEFAULT_PUBLISHER),
            "input_summary_sha256": input_summary_sha256(snapshot.get("forecast_result", {})),
            "artifact_type": "snapshot",
            "artifact_id": snapshot.get("snapshot_id"),
            "note": "revenue_backtest create",
        }
    )


def lookup(input_sha256: str) -> list[dict[str, Any]]:
    """Return the full publication history of one input anchor (raises on corruption)."""
    return [entry for entry in _read_entries() if entry["input_sha256"] == input_sha256]


def is_registered(input_sha256: str) -> bool:
    """True when the anchor appears in the registry (fail-closed on corruption)."""
    return any(entry["input_sha256"] == input_sha256 for entry in _read_entries())


def audit(result_files: list[Path] | None = None, *, since: str | None = None) -> list[str]:
    """Report registry problems: corruption, same-anchor conflicts, unregistered claims."""
    problems: list[str] = []
    try:
        entries = _read_entries()
    except RegistryError as exc:
        return [str(exc)]
    if since is not None:
        entries = [entry for entry in entries if entry.get("registered_at", "") >= since]
    # Conflict = the same input anchored to different results *within one
    # engine/schema generation and artifact type* (the D2 forgery shape).
    # Cross-version result differences (same input re-run under a newer
    # engine) and forecast-vs-snapshot pairs (different artifact types
    # referencing the same anchor) are normal history.
    by_generation: dict[tuple[str, str, str, str], set[str]] = {}
    for entry in entries:
        generation = (
            entry["input_sha256"],
            entry.get("engine_version"),
            entry.get("schema_version"),
            entry.get("artifact_type", "forecast"),
        )
        by_generation.setdefault(generation, set()).add(entry["result_sha256"])
    for (anchor, engine, schema, artifact_type), result_hashes in by_generation.items():
        if len(result_hashes) > 1:
            problems.append(
                f"conflict: input {anchor[:16]}... (engine {engine}, schema {schema}, "
                f"{artifact_type}) registered {len(result_hashes)} distinct result hashes"
            )
    registered_anchors = {entry["input_sha256"] for entry in entries}
    for path in result_files or []:
        try:
            artifact = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            problems.append(f"unreadable result artifact {path}: {exc}")
            continue
        claimed = artifact.get("input_sha256")
        if not isinstance(claimed, str) or claimed not in registered_anchors:
            problems.append(
                f"unregistered claim: {path} anchors input "
                f"{(claimed or '?')[:16]} which was never registered"
            )
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Query and audit the append-only publication registry"
    )
    command = parser.add_subparsers(dest="command", required=True)
    lookup_parser = command.add_parser("lookup", help="publication history of one input anchor")
    lookup_parser.add_argument("--input-sha", required=True)
    audit_parser = command.add_parser("audit", help="detect conflicts / corruption / unregistered claims")
    audit_parser.add_argument("--result", action="append", type=Path, help="result artifact to cross-check")
    audit_parser.add_argument("--since", help="only consider entries registered at/after this ISO timestamp")
    args = parser.parse_args()
    if args.command == "lookup":
        for entry in lookup(args.input_sha):
            print(json.dumps(entry, ensure_ascii=False, sort_keys=True))
        return 0
    if args.command == "audit":
        problems = audit(args.result, since=args.since)
        for problem in problems:
            print(problem)
        return 1 if problems else 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
