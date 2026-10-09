"""Bounded registered originals, including inactive inventory (never consumer eligibility)."""

from __future__ import annotations
from dataclasses import dataclass
import os
from pathlib import Path
import time
from typing import Any
from .resolver import _ReadBudget, _inside_configured_roots, _read_verified_bytes
from .policy import _effective_reusable
from .source_reader import SourceReadError, SourceRef, _relative_segments


@dataclass(frozen=True)
class LocalPrepareLimits:
    max_candidates: int = 16
    max_bytes: int = 268435456
    timeout_seconds: float = 30.0

    def __post_init__(self):
        if type(self.max_candidates) is not int or not 1 <= self.max_candidates <= 256:
            raise ValueError("invalid local candidate limit")
        if type(self.max_bytes) is not int or not 1 <= self.max_bytes <= 1073741824:
            raise ValueError("invalid local byte limit")
        if (
            isinstance(self.timeout_seconds, bool)
            or not isinstance(self.timeout_seconds, (int, float))
            or not 0 < self.timeout_seconds <= 600
        ):
            raise ValueError("invalid local deadline")


class LocalReadBudget(_ReadBudget):
    def __init__(self, limits: LocalPrepareLimits):
        super().__init__(
            max_candidates=limits.max_candidates, max_bytes=limits.max_bytes
        )
        self.deadline = time.monotonic() + limits.timeout_seconds

    def check(self):
        if time.monotonic() >= self.deadline:
            raise SourceReadError("unavailable", "local_prepare_deadline")
        if self.cancelled:
            raise SourceReadError("unavailable", "cancelled")

    def take_candidate(self):
        self.check()
        return super().take_candidate()

    def charge(self, size):
        self.check()
        return super().charge(size)


@dataclass(frozen=True)
class LocalOriginal:
    ref: SourceRef
    data: bytes
    locations: tuple[tuple[str, Path, Any], ...]
    failures: tuple[str, ...]


def observe_document(catalog, document_id: str) -> dict[str, Any]:
    row = catalog.reader.exact_source_version(document_id)
    if row is None:
        raise SourceReadError("not_indexed", "document_not_indexed")
    audits = [
        dict(x)
        for x in catalog.reader.fetchall(
            "SELECT * FROM document_retire_audit WHERE document_id=? ORDER BY rowid LIMIT 65",
            (document_id,),
        )
    ]
    if len(audits) > 64:
        raise SourceReadError("blocked", "retirement_history_limit")
    locations = [
        dict(x)
        for x in catalog.reader.exact_source_locations(document_id, row["source_id"])
    ]
    if len(locations) > 256:
        raise SourceReadError("unavailable", "local_location_limit")
    assertions = [
        dict(x)
        for x in catalog.reader.fetchall(
            "SELECT assertion_id,created_at FROM source_metadata_assertions WHERE document_id=? ORDER BY rowid DESC LIMIT 1",
            (document_id,),
        )
    ]
    return {
        "version": dict(row),
        "retire_audit": audits,
        "locations": locations,
        "latest_assertion": assertions,
    }


def metadata_retirement(observation: dict[str, Any]) -> bool:
    """Closed known-producer history, never a substring or issuer/hash whitelist."""
    audits = observation["retire_audit"]
    if not audits:
        return False
    proven = False
    for audit in audits:
        pair = (audit["reason"], audit["created_by"])
        if pair == (
            "legacy sidecar lacks source_url; batch governance Phase 15.6 (F13)",
            "phase-15.6-governance",
        ):
            proven = True
        elif (
            pair
            == (
                "phase-15.6 audit reconciliation (reconcile-retire)",
                "reconcile-retire-20260806",
            )
            and proven
        ):
            pass
        elif pair == ("source_metadata_insufficient", "automated-source-metadata"):
            proven = True
        else:
            return False
    return proven


def verify_registered_original(
    catalog, ref: SourceRef, *, budget: LocalReadBudget
) -> LocalOriginal:
    """Verify actual registered inactive bytes without inventing an active handle."""
    row = catalog.reader.exact_source_version(ref.document_id)
    if row is None or (
        row["source_id"],
        row["content_sha256"],
        row["byte_size"],
        row["mime_type"],
    ) != (ref.source_id, ref.content_sha256, ref.byte_size, ref.mime_type):
        raise SourceReadError("unavailable", "source_ref_changed")
    roots = {x.root_id: x for x in catalog.config.roots}
    rows = catalog.reader.exact_source_locations(ref.document_id, ref.source_id)
    if len(rows) > 256:
        raise SourceReadError("unavailable", "local_location_limit")
    valid = []
    failures = []
    first = None
    for loc in sorted(
        rows,
        key=lambda x: (
            roots[x["root_id"]].priority if x["root_id"] in roots else 999999,
            x["root_id"],
            x["relative_path"],
        ),
    ):
        budget.check()
        root = roots.get(loc["root_id"])
        if (
            root is None
            or not _effective_reusable(root, catalog.config)
            or (root.allowed_statuses and "active" not in root.allowed_statuses)
        ):
            failures.append("root_admission_denied")
            continue
        if (
            root.allowed_document_kinds
            and row["document_kind"] not in root.allowed_document_kinds
        ) or (root.max_file_size is not None and ref.byte_size > root.max_file_size):
            failures.append("root_admission_denied")
            continue
        segments = _relative_segments(str(loc["relative_path"]))
        if (
            loc["role"] != "original_primary"
            or loc["location_status"] not in {"active", "retired"}
            or segments is None
            or ".rejections" in segments
        ):
            failures.append("location_ineligible")
            continue
        resolved = Path(os.path.realpath(root.path.joinpath(*segments)))
        if not _inside_configured_roots(resolved, (root,)):
            failures.append("artifact_path_outside_allowed_root")
            continue
        data, status, reason, detail = _read_verified_bytes(
            resolved,
            expected_sha256=ref.content_sha256,
            expected_byte_size=ref.byte_size,
            budget=budget,
            retain_bytes=first is None,
        )
        if status:
            failures.append(reason or status)
            if reason in {"cancelled", "budget_exceeded"}:
                break
            continue
        if first is None:
            first = data
        valid.append((loc["location_id"], resolved, root))
    if first is None:
        raise SourceReadError(
            "unavailable", "no_verified_location", ",".join(sorted(set(failures)))
        )
    return LocalOriginal(ref, first, tuple(valid), tuple(failures))
