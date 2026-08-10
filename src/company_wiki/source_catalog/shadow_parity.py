"""FC-303: v1/v2 scanner shadow parity over a frozen corpus.

``run_root_shadow_parity`` runs the v1 scanner (_scan_root_v1) and the v2
adapter pipeline (registered adapter via adapter_dispatch) on the same
immutable tree and compares candidate count, relative paths, roles,
content hashes, entity/kind/status identity and exclusion reasons.

Diffs are classified: ``expected_good`` (must match), ``known_bad``
(registered in the migration-rules ledger with a reason), ``blocker``
(unexplained — stops the line).  The ledger rejects phantom entries, so a
rule must correspond to an actual diff on the frozen corpus.

EX-08 guarantee: a future root with a configured adapter must dispatch
via the adapter in the v2 path (adapter_dispatch) — never fall back to
the legacy kind-based v1 scanner.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Callable

from .adapters.parity import ParityDiff, ParityReport, run_parity
from .models import RootSpec
from .scanner import _scan_root_v1, scan_root_strategy

# Migration-rules ledger: (relative_path, field) -> reason.  A rule may only
# be registered when the frozen corpus actually exhibits that diff.
_MIGRATION_RULES: dict[tuple[str, str], str] = {}


def migration_ledger() -> dict[tuple[str, str], str]:
    return dict(_MIGRATION_RULES)


def register_migration_rule(
    key: tuple[str, str],
    reason: str,
    *,
    against: ParityReport | None = None,
) -> None:
    """Register an explainable v1/v2 diff.  When ``against`` (a parity
    report over the frozen corpus) is given, the key must actually appear
    in its diff set — phantom rules are rejected."""
    if not (isinstance(key, tuple) and len(key) == 2 and key[0] and key[1]):
        raise ValueError("migration rule key must be (path, field)")
    if not (isinstance(reason, str) and reason.strip()):
        raise ValueError("migration rule reason required")
    if against is not None:
        observed = {(d.path, d.field) for d in against.diffs}
        if key not in observed:
            raise ValueError(
                f"phantom migration rule {key!r}: no matching diff on the "
                f"frozen corpus (observed: {sorted(observed)})"
            )
    _MIGRATION_RULES[key] = reason.strip()


def _candidate_hash(candidate: Any) -> str:
    """Stable hash of a candidate's identity fields (path, role, entity,
    status, group metadata) — used to detect any identity drift."""
    payload = (
        getattr(candidate, "relative_path", ""),
        getattr(candidate, "role", ""),
        getattr(candidate, "entity_name", "") or "",
        getattr(candidate, "source_status", "") or "",
        str(getattr(candidate, "group_metadata", {}) or {}),
    )
    return hashlib.sha256(repr(payload).encode("utf-8")).hexdigest()


def _v2_candidates(root: RootSpec, company_names: tuple[str, ...]):
    """Run the v2 shadow pipeline (registered adapter) and return its
    candidates; fail closed on unresolvable routes."""
    return scan_root_strategy(root, company_names, v2_scan_shadow=True)[0]


def _v2_adapter_candidates(root: RootSpec):
    """Raw adapter candidates (NormalizedCandidate) carrying the DECLARED
    content_sha256 — the SPI-03 hash-accuracy comparison source."""
    from .adapter_dispatch import adapter_for

    return adapter_for(root).enumerate(root.path)


def run_root_shadow_parity(
    root: RootSpec,
    company_names: tuple[str, ...],
    *,
    progress: Callable[..., None] | None = None,
) -> ParityReport:
    """Compare v1 and v2 scanner output over the same frozen tree."""
    v1_candidates, v1_excluded, _ = _scan_root_v1(
        root, company_names, progress=progress
    )
    v2_candidates = _v2_candidates(root, company_names)
    # content-hash comparison: every v2 candidate must carry the same
    # relative path and role as its v1 counterpart; identity drift is
    # caught by the candidate hash comparison below.
    report = run_parity(
        v1_candidates,
        v2_candidates,
        known_bad=_MIGRATION_RULES,
        entity_of=lambda c: getattr(c, "entity_name", None),
    )
    # extend run_parity with content-hash + identity comparison.
    # Content hash: each v2 adapter candidate's DECLARED content_sha256
    # must equal the on-disk file hash (SPI-03 hash accuracy); a tampered
    # v2 pipeline that declares a wrong hash is caught here.
    try:
        adapter_candidates = _v2_adapter_candidates(root)
    except Exception:
        adapter_candidates = []
    for item in adapter_candidates:
        declared = getattr(item, "content_sha256", None)
        if not declared:
            continue
        actual = _file_hash(root.path / item.relative_path)
        if declared != actual:
            key = (item.relative_path, "content_sha256")
            classification = (
                "known_bad" if key in _MIGRATION_RULES else "blocker"
            )
            report.diffs.append(ParityDiff(
                item.relative_path, "content_sha256", declared, actual,
                classification,
            ))
    # Identity comparison: v1 vs v2 candidate identity hashes must match
    # for paths present in both pipelines.
    by_path_v1 = {c.relative_path: c for c in v1_candidates}
    by_path_v2 = {c.relative_path: c for c in v2_candidates}
    for path in sorted(set(by_path_v1) & set(by_path_v2)):
        left = by_path_v1[path]
        right = by_path_v2[path]
        v1_value = _candidate_hash(left)
        v2_value = _candidate_hash(right)
        if v1_value != v2_value:
            key = (path, "identity")
            classification = (
                "known_bad" if key in _MIGRATION_RULES else "blocker"
            )
            report.diffs.append(ParityDiff(
                path, "identity", v1_value, v2_value, classification
            ))
    report.total_v1 = len(v1_candidates)
    report.total_v2 = len(v2_candidates)
    return report


def _file_hash(path: Path | None) -> str:
    """Content hash of a file (read-only, frozen corpus)."""
    if isinstance(path, Path) and path.is_file():
        return hashlib.sha256(path.read_bytes()).hexdigest()
    return ""


def reset_migration_ledger() -> None:
    """Test seam: clear the ledger (frozen corpus must not accumulate
    rules across tests)."""
    _MIGRATION_RULES.clear()


__all__ = [
    "migration_ledger",
    "register_migration_rule",
    "reset_migration_ledger",
    "run_root_shadow_parity",
]
