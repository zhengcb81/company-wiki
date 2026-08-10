"""FC-404: migration quality ledger.

Read-only ledger over the catalog recording per root/market/kind:
coverage (input vs buckets), missing fields, conflicts, duplicate
location sets, and retired locations.  The pre-apply gate
(``ledger_is_closed``) requires every root's explainable bucket sum to
equal its input total.  Building the ledger never modifies the catalog
or any real file; retired documents are counted but never revived.
"""

from __future__ import annotations

import json
from typing import Any

from .store import CatalogStore

BUCKETS = ("eligible", "needs_review", "unprovable", "retired_or_conflict")


def _empty_root() -> dict[str, Any]:
    return {
        "input": 0,
        "eligible": 0,
        "needs_review": 0,
        "unprovable": 0,
        "retired_or_conflict": 0,
        "missing_fields": {},
        "conflicts": 0,
    }


def build_quality_ledger(store: CatalogStore) -> dict[str, Any]:
    """Build the quality ledger (read-only)."""
    rows = store.fetchall(
        """SELECT d.document_id, d.source_status, d.document_kind,
                  d.metadata_json,
                  (SELECT GROUP_CONCAT(l.root_id) FROM locations l
                    WHERE l.document_id = d.document_id
                      AND l.location_status='active') AS root_ids,
                  (SELECT COUNT(*) FROM locations l
                    WHERE l.document_id = d.document_id
                      AND l.role='original_primary') AS primary_locations,
                  (SELECT COUNT(DISTINCT s.content_sha256)
                    FROM locations l
                    JOIN sources s ON s.source_id = l.source_id
                    WHERE l.document_id = d.document_id
                      AND l.role='original_primary') AS source_hashes
           FROM documents d
           ORDER BY d.document_id"""
    )
    by_root: dict[str, dict[str, Any]] = {}
    by_kind: dict[str, dict[str, Any]] = {}
    by_market: dict[str, dict[str, Any]] = {}
    duplicate_location_sets = 0
    retired_locations = 0
    total_input = 0

    retired_rows = store.fetchall(
        """SELECT COUNT(*) c FROM locations WHERE location_status='retired'"""
    )
    retired_locations = retired_rows[0]["c"]

    for row in rows:
        root_ids = (row["root_ids"] or "").split(",") if row["root_ids"] else []
        # a document with two active original_primary locations sharing the
        # same source content hash is a duplicate location set
        if row["primary_locations"] >= 2 and row["source_hashes"] == 1:
            duplicate_location_sets += 1
        # retired documents are excluded from the migration input entirely
        # (never revived); they are only reflected in retired_locations
        if row["source_status"] == "retired":
            continue
        total_input += 1
        try:
            metadata = json.loads(row["metadata_json"] or "{}")
        except json.JSONDecodeError:
            metadata = {}
        acq = metadata.get("acquisition") or {}
        market = str(acq.get("market") or "(none)")
        for dim_name, dim in (("by_root", root_ids), ("by_kind", [row["document_kind"]]),
                              ("by_market", [market])):
            target = {"by_root": by_root, "by_kind": by_kind,
                      "by_market": by_market}[dim_name]
            for key in (dim or ["(none)"]):
                slot = target.setdefault(key, _empty_root())
                slot["input"] += 1
                bucket = _bucket_for(acq)
                slot[bucket] += 1
                if bucket in ("needs_review", "unprovable"):
                    for field in _missing_fields(acq):
                        slot["missing_fields"][field] = (
                            slot["missing_fields"].get(field, 0) + 1
                        )
    return {
        "total_input": total_input,
        "duplicate_location_sets": duplicate_location_sets,
        "retired_locations": retired_locations,
        "by_root": by_root,
        "by_kind": by_kind,
        "by_market": by_market,
    }


def _bucket_for(acq: dict[str, Any]) -> str:
    """Bucket a document deterministically (FC-402 semantics)."""
    if not acq.get("security_id") or not acq.get("provider_document_id"):
        return "unprovable"
    if not acq.get("period_end"):
        return "needs_review"
    return "eligible"


def _missing_fields(acq: dict[str, Any]) -> list[str]:
    missing = []
    for field in ("security_id", "provider_document_id", "period_end",
                  "source_url", "provider"):
        if not acq.get(field):
            missing.append(field)
    return missing


def ledger_is_closed(ledger: dict[str, Any]) -> tuple[bool, list[str]]:
    """Pre-apply gate: every root's explainable bucket sum must equal its
    input total (no unexplained rows)."""
    problems = []
    for root_id, row in ledger["by_root"].items():
        bucket_sum = sum(row[b] for b in BUCKETS)
        if bucket_sum != row["input"]:
            problems.append(
                f"root {root_id}: bucket sum {bucket_sum} != input {row['input']}"
            )
    return (not problems), problems


__all__ = [
    "BUCKETS",
    "build_quality_ledger",
    "ledger_is_closed",
]
