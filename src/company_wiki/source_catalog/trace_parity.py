"""FC-601: CompanyRawAdapter 等价 — full-trace parity over a frozen corpus.

``candidate_trace`` projects a candidate list into the five traces the
catalog records — sources, documents, locations, handles, bundles — and
``run_trace_parity`` diffs the v1 scanner path against the v2 adapter
path over the same immutable tree with the FC-303 migration-ledger
semantics (unexplained diffs block).  The projection is deterministic and
golden-tested: a projection bug breaks the golden test even when both
sides share the projection.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Callable

from .adapters.parity import ParityDiff, ParityReport
from .models import RootSpec
from .scanner import _scan_root_v1, scan_root_strategy
from .shadow_parity import migration_ledger

_MIME_BY_SUFFIX = {
    ".pdf": "application/pdf",
    ".json": "application/json",
    ".html": "text/html",
    ".htm": "text/html",
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


def _mime_type(path: Path) -> str:
    return _MIME_BY_SUFFIX.get(path.suffix.lower(), "application/octet-stream")


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _trace_entry(candidate: Any) -> dict[str, Any]:
    """The candidate's path (None when the file vanished mid-scan)."""
    path = getattr(candidate, "path", None)
    if path is None or not Path(path).is_file():
        return {}
    return {
        "content_sha256": _sha256_file(path),
        "byte_size": Path(path).stat().st_size,
        "mime_type": _mime_type(Path(path)),
        "role": getattr(candidate, "role", ""),
        "location_status": str(getattr(candidate, "source_status", "") or ""),
        "document_kind": str(
            getattr(candidate, "group_metadata", {}).get("document_kind") or ""
        ),
        "title": str(
            getattr(candidate, "group_metadata", {}).get("source_title")
            or Path(path).stem
        ),
    }


def candidate_trace(candidates: list[Any]) -> dict[str, Any]:
    """Deterministic projection of a candidate list into the five traces:
    sources, documents, locations, handles, bundles (keyed by relative
    path or group key; sorted bundles)."""
    sources: dict[str, dict[str, Any]] = {}
    documents: dict[str, dict[str, Any]] = {}
    locations: dict[str, dict[str, Any]] = {}
    handles: dict[str, dict[str, Any]] = {}
    bundles: dict[str, list[tuple[str, str]]] = {}

    for candidate in candidates:
        relative = str(getattr(candidate, "relative_path", ""))
        entry = _trace_entry(candidate)
        if not entry:
            continue
        sources[relative] = {
            "content_sha256": entry["content_sha256"],
            "byte_size": entry["byte_size"],
            "mime_type": entry["mime_type"],
        }
        documents[relative] = {
            "content_sha256": entry["content_sha256"],
            "source_status": entry["location_status"],
            "document_kind": entry["document_kind"],
            "title": entry["title"],
        }
        locations[relative] = {
            "role": entry["role"],
            "location_status": entry["location_status"],
        }
        group_metadata = getattr(candidate, "group_metadata", {}) or {}
        if entry["role"] == "original_primary" and group_metadata.get("security_id"):
            handles[relative] = {
                "market": str(group_metadata.get("market") or ""),
                "security_id": str(group_metadata.get("security_id") or ""),
                "fiscal_year": group_metadata.get("fiscal_year"),
                "period_end": group_metadata.get("period_end"),
                "provider": str(group_metadata.get("provider") or ""),
                "provider_document_id": str(
                    group_metadata.get("provider_document_id") or ""
                ),
            }
        group_key = str(getattr(candidate, "group_key", "") or relative)
        bundles.setdefault(group_key, []).append(
            (relative, entry["content_sha256"])
        )
    return {
        "sources": sources,
        "documents": documents,
        "locations": locations,
        "handles": handles,
        "bundles": {
            key: tuple(sorted(value)) for key, value in sorted(bundles.items())
        },
    }


def _compare_section(
    name: str,
    v1_section: dict[str, Any],
    v2_section: dict[str, Any],
    known_bad: dict[tuple[str, str], str],
    diffs: list[ParityDiff],
) -> None:
    for key in sorted(set(v1_section) | set(v2_section)):
        left = v1_section.get(key)
        right = v2_section.get(key)
        if left is None or right is None:
            field = "presence"
            value = "v1-only" if right is None else "v2-only"
            classification = (
                "known_bad" if (f"{name}:{key}", field) in known_bad else "blocker"
            )
            diffs.append(ParityDiff(
                f"{name}:{key}", field, value, value, classification
            ))
            continue
        for field_name in sorted(set(left) | set(right)):
            v1_value = left.get(field_name)
            v2_value = right.get(field_name)
            if v1_value != v2_value:
                classification = (
                    "known_bad"
                    if (f"{name}:{key}", field_name) in known_bad
                    else "blocker"
                )
                diffs.append(ParityDiff(
                    f"{name}:{key}", field_name,
                    v1_value, v2_value, classification,
                ))


def compare_traces(
    v1_trace: dict[str, Any],
    v2_trace: dict[str, Any],
    *,
    known_bad: dict[tuple[str, str], str] | None = None,
) -> ParityReport:
    """Diff two traces section by section with FC-303 ledger semantics."""
    known_bad = known_bad or {}
    diffs: list[ParityDiff] = []
    for section in ("sources", "documents", "locations", "handles"):
        _compare_section(
            section, v1_trace[section], v2_trace[section], known_bad, diffs
        )
    # bundles hold plain sorted tuples — compare whole values
    for key in sorted(set(v1_trace["bundles"]) | set(v2_trace["bundles"])):
        left = v1_trace["bundles"].get(key)
        right = v2_trace["bundles"].get(key)
        if left is None or right is None:
            value = "v1-only" if right is None else "v2-only"
            classification = (
                "known_bad" if (f"bundles:{key}", "presence") in known_bad
                else "blocker"
            )
            diffs.append(ParityDiff(
                f"bundles:{key}", "presence", value, value, classification
            ))
            continue
        if left != right:
            classification = (
                "known_bad" if (f"bundles:{key}", "value") in known_bad
                else "blocker"
            )
            diffs.append(ParityDiff(
                f"bundles:{key}", "value", left, right, classification
            ))
    report = ParityReport(
        total_v1=sum(len(v1_trace[s]) for s in v1_trace),
        total_v2=sum(len(v2_trace[s]) for s in v2_trace),
    )
    report.diffs = diffs
    return report


def run_trace_parity(
    root: RootSpec,
    company_names: tuple[str, ...],
    *,
    progress: Callable[..., None] | None = None,
) -> ParityReport:
    """Compare the v1 scanner path and the v2 adapter path over the same
    frozen tree on the full source/document/location/handle/bundle trace."""
    v1_candidates, _, _ = _scan_root_v1(root, company_names, progress=progress)
    v2_candidates = scan_root_strategy(root, company_names, v2_scan_shadow=True)[0]
    return compare_traces(
        candidate_trace(v1_candidates),
        candidate_trace(v2_candidates),
        known_bad=migration_ledger(),
    )


__all__ = [
    "candidate_trace",
    "compare_traces",
    "run_trace_parity",
]
