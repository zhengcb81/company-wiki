"""Historical scanner rollout decoding, excluded from current scan selection.

Existing replay callers can import these compatibility functions. Current
registration/discovery uses configured adapters and never reads this state.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

class CutoverGateError(RuntimeError):
    """FC-305: the two-round zero-diff gate has not passed — production
    dry shadow with v2 is refused."""


def cutover_decision(snapshot: dict[str, Any]) -> str:
    """FC-305: per-cohort v2 enablement — v2 when the snapshot's
    v2_scan_shadow flag is on, v1 otherwise (v1 stays the read-only
    fallback until the gate passes)."""
    flags = snapshot.get("flags", {}) if isinstance(snapshot, dict) else {}
    return "v2" if flags.get("v2_scan_shadow") else "v1"


def v2_scan_shadow_from_snapshot(catalog_dir: Path | str) -> bool:
    """GP-002: resolve the physical scan mode from the activation snapshot
    (``catalog_dir/runtime_policy.json``) for every scan entry that writes
    the catalog.

    No snapshot file = v1 (the legacy default — temp projects and tooling
    never activated a snapshot).  A present-but-invalid snapshot degrades
    to v1 rather than crashing the scan: scanning is a read-heavy catalog
    operation with no external data exposure, so silent v1 is safe.  (The
    LLM exit gate in GP-003 applies stricter fail-closed semantics when
    data leaves the catalog to an external model.)
    """
    from .runtime_policy import RuntimePolicyError, load_runtime_policy

    snapshot_path = Path(catalog_dir) / "runtime_policy.json"
    if not snapshot_path.is_file():
        return False
    try:
        return cutover_decision(load_runtime_policy(snapshot_path)) == "v2"
    except (RuntimePolicyError, KeyError, TypeError):
        return False


def gate_production_dry_shadow(
    round_diffs: list[list[Any]], *, rounds_required: int = 2
) -> bool:
    """FC-305: production dry shadow requires the last ``rounds_required``
    consecutive shadow rounds to each have zero unexplained diffs.

    ``round_diffs`` is one entry per recorded shadow round (the diff list
    of that round; empty = zero diffs).  Fewer rounds than required, or a
    diff in any required round, fails the gate."""
    if rounds_required < 2:
        return False
    if len(round_diffs) < rounds_required:
        return False
    return all(len(round) == 0 for round in round_diffs[-rounds_required:])
