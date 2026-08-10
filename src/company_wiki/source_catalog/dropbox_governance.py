"""FC-503: sidecar-root historical candidate governance (read-only).

``inventory_dropbox`` walks a sidecar-shaped external root through the
production adapter dispatch (the same chain FC-502 pins), classifies
every candidate into the FC-402 buckets, reports missing fields and
location sets duplicated into other roots (ids come from the caller,
never hardcoded — FC-304), and keeps 中国平安-style weak-identity samples
unprovable.  The inventory NEVER writes: the report embeds a per-file
fingerprint so a second run proves zero writes, the catalog is opened
read-only, and other roots' copies are never deleted to fabricate
exclusive-source proof.
"""

from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path
from typing import Any

from .adapter_dispatch import scan_root_via_adapter
from .backfill_v2 import classify_bucket
from .models import RootSpec

PINGAN_PATH_HINT = "中国平安"


class GovernanceError(RuntimeError):
    """Raised when the inventory guard fails closed."""


def _is_pingan_candidate(relative_path: str, group_metadata: dict) -> bool:
    return PINGAN_PATH_HINT in relative_path or PINGAN_PATH_HINT in str(
        group_metadata.get("display_name") or ""
    )


def _catalog_counts(db: Path) -> tuple[int, int, int] | None:
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        counts = tuple(
            con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            for t in ("documents", "sources", "locations")
        )
    finally:
        con.close()
    return counts


def _duplicate_sets(
    catalog: Path,
    fingerprint: dict[str, tuple[int, int, str]],
    other_root_ids: tuple[str, ...],
) -> dict[str, Any]:
    """Location sets whose ACTUAL file bytes also have an active location
    in another root (the on-disk content hash is the ground truth, not the
    sidecar-declared one).  Read-only query; nothing is deleted or hidden."""
    hashes = {
        digest
        for relative, (_size, _mtime, digest) in fingerprint.items()
        if not relative.endswith(".source.json") and digest
    }
    if not hashes or not other_root_ids:
        return {"count": 0, "samples": []}
    con = sqlite3.connect(f"file:{catalog}?mode=ro", uri=True)
    try:
        placeholders = ",".join("?" for _ in hashes)
        root_ids = ",".join("?" for _ in other_root_ids)
        rows = con.execute(
            f"""SELECT s.content_sha256, l.root_id, l.relative_path,
                       COUNT(*) AS n
                FROM locations l
                JOIN sources s ON s.source_id = l.source_id
                WHERE l.root_id IN ({root_ids})
                  AND l.location_status = 'active'
                  AND s.content_sha256 IN ({placeholders})
                GROUP BY s.content_sha256, l.root_id, l.relative_path
                ORDER BY s.content_sha256""",
            (*other_root_ids, *sorted(hashes)),
        ).fetchall()
    finally:
        con.close()
    per_hash: dict[str, dict[str, Any]] = {}
    for sha, root_id, rel, n in rows:
        slot = per_hash.setdefault(sha, {"root_ids": [], "locations": 0})
        if root_id not in slot["root_ids"]:
            slot["root_ids"].append(root_id)
        slot["locations"] += n
    samples = [
        {
            "content_sha256": h,
            "relative_path": str(
                next(relative for relative, (_s, _m, digest) in fingerprint.items()
                     if digest == h and not relative.endswith(".source.json")),
            ),
            "root_ids": sorted(slot["root_ids"]),
            "other_root_locations": slot["locations"],
        }
        for h, slot in sorted(per_hash.items())
    ]
    return {"count": len(samples), "samples": samples[:10]}


def _fingerprint_file(path: Path) -> tuple[int, int, str]:
    st = path.stat()
    return st.st_size, st.st_mtime_ns, hashlib.sha256(path.read_bytes()).hexdigest()


def inventory_dropbox(
    root: RootSpec,
    *,
    catalog: Path | None = None,
    other_root_ids: tuple[str, ...] = (),
    company_names: tuple[str, ...] = (),
) -> dict[str, Any]:
    """Read-only governance inventory of a sidecar-shaped root.

    Never writes: candidates come from the adapter dispatch, the catalog
    is opened ``mode=ro``, and the report embeds a per-file fingerprint
    (size, mtime, sha256) that a second run can compare.
    """
    counts_before = _catalog_counts(catalog) if catalog else None
    candidates = scan_root_via_adapter(root, company_names)
    by_role: dict[str, int] = {}
    buckets: dict[str, int] = {
        "eligible": 0, "needs_review": 0, "unprovable": 0,
        "retired_or_conflict": 0,
    }
    missing_fields: dict[str, int] = {}
    pingan_path = 0
    pingan_unprovable = 0
    pingan_eligible = 0
    fingerprint: dict[str, tuple[int, int, str]] = {}

    for candidate in candidates:
        relative = candidate.relative_path
        primary = candidate.path
        sidecar = primary.with_name(primary.name + ".source.json")
        if primary.is_file():
            fingerprint[relative] = (
                primary.stat().st_size,
                primary.stat().st_mtime_ns,
                hashlib.sha256(primary.read_bytes()).hexdigest(),
            )
        if sidecar.is_file():
            fingerprint[sidecar.relative_to(root.path).as_posix()] = (
                _fingerprint_file(sidecar)
            )
        by_role[candidate.role] = by_role.get(candidate.role, 0) + 1
        pingan = _is_pingan_candidate(relative, candidate.group_metadata)
        if pingan:
            pingan_path += 1
        acq = {k: v for k, v in candidate.group_metadata.items()
               if k not in ("schema_version", "adapter_id",
                            "adapter_version", "normalization_status",
                            "published_at", "filed_at", "accepted_at",
                            "language", "revision_id")}
        # the sidecar declares document_kind; it serves as the strong gate's
        # form_type (declared metadata, never inferred from the file name)
        if acq.get("document_kind") and not acq.get("form_type"):
            acq["form_type"] = acq["document_kind"]
        bucket, missing = classify_bucket(acq)
        buckets[bucket] += 1
        for field in missing:
            missing_fields[field] = missing_fields.get(field, 0) + 1
        if pingan:
            if bucket == "unprovable":
                pingan_unprovable += 1
            if bucket == "eligible":
                pingan_eligible += 1
                raise GovernanceError(
                    f"FC-503: 中国平安 candidate {relative!r} classified "
                    f"eligible without reviewer-completed evidence"
                )
    return {
        "candidates_total": len(candidates),
        "by_role": by_role,
        "buckets": buckets,
        "missing_fields": missing_fields,
        "duplicate_location_sets": (
            _duplicate_sets(catalog, fingerprint, other_root_ids)
            if catalog else {"count": 0, "samples": []}
        ),
        "pingan": {
            "path_candidates": pingan_path,
            "unprovable": pingan_unprovable,
            "eligible": pingan_eligible,
        },
        "fingerprint": fingerprint,
        "catalog_counts": counts_before,
        "writes": 0,
    }


__all__ = [
    "GovernanceError",
    "inventory_dropbox",
]
