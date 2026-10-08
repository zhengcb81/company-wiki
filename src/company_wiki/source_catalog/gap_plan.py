"""WU-4.2: metadata-only discovery alignment and GapPlan.

``build_gap_plan`` is a pure function aligning local reusable handles with
remote provider metadata (DownloadCandidates from ``adapter.discover`` —
metadata only, nothing is fetched here). It answers: what can be reused,
what is genuinely missing, which revisions are stale, and whether the
provider state is even known.

Rules (task_plan WU-4.2):

- local is latest for a period → reuse (download=0);
- provider published a NEWER period (filing_date ≤ as_of) local lacks →
  missing;
- same period, provider accession newer → newer_revision (replacement);
- provider knows nothing beyond local latest → not_published, gap=0;
- provider offline/rate-limited → provider_unavailable, keep local,
  NEVER claim up-to-date;
- remote metadata filed after as_of → future (excluded from gap).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from .qualification import qualify_source


GAP_PLAN_SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class GapPlan:
    schema_version: str
    request_id: str
    as_of_date: str
    document_kind: str
    entity: str
    market: str
    reuse: tuple[Any, ...] = ()
    missing: tuple[Any, ...] = ()
    newer_revision: tuple[Any, ...] = ()
    not_published: bool = False
    provider_unavailable: bool = False
    provider_reason: str | None = None
    future: tuple[Any, ...] = ()
    gap_hash: str = ""
    publication_unknown: tuple[Any, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        result = {
            "schema_version": self.schema_version,
            "request_id": self.request_id,
            "as_of_date": self.as_of_date,
            "document_kind": self.document_kind,
            "entity": self.entity,
            "market": self.market,
            "reuse": [h.to_dict() if hasattr(h, "to_dict") else h for h in self.reuse],
            "missing": [
                c.to_dict() if hasattr(c, "to_dict") else c for c in self.missing
            ],
            "newer_revision": [
                c.to_dict() if hasattr(c, "to_dict") else c for c in self.newer_revision
            ],
            "not_published": self.not_published,
            "provider_unavailable": self.provider_unavailable,
            "provider_reason": self.provider_reason,
            "future": [
                c.to_dict() if hasattr(c, "to_dict") else c for c in self.future
            ],
            "gap_hash": self.gap_hash,
        }
        if self.publication_unknown:
            result["publication_unknown"] = [
                c.to_dict() if hasattr(c, "to_dict") else c for c in self.publication_unknown
            ]
        return result


def _candidate_year(candidate: Any) -> int | None:
    return getattr(candidate, "fiscal_year", None)


def _candidate_filed(candidate: Any) -> str | None:
    return getattr(candidate, "filing_date", None)


def _candidate_accession(candidate: Any) -> str:
    return str(getattr(candidate, "provider_document_id", "") or "")


def _candidate_amended(candidate: Any) -> bool:
    return bool(getattr(candidate, "amended", False))


def build_gap_plan(
    *,
    request_id: str,
    as_of_date: str,
    document_kind: str,
    entity: str,
    market: str,
    local_handles: list[Any],
    remote_candidates: list[Any],
    provider_error: str | None = None,
) -> GapPlan:
    """Align already-admitted local sources with remote provider metadata."""
    # URL and collector completeness remain handle diagnostics. Reuse
    # eligibility is decided by the resolver's identity, period, publication
    # cutoff and byte checks; the planner must not repeat a metadata gate.
    local_handles = list(local_handles)
    if provider_error:
        return GapPlan(
            schema_version=GAP_PLAN_SCHEMA_VERSION,
            request_id=request_id,
            as_of_date=as_of_date,
            document_kind=document_kind,
            entity=entity,
            market=market,
            reuse=tuple(local_handles),
            provider_unavailable=True,
            provider_reason=provider_error,
            gap_hash=_hash_gap(
                request_id=request_id,
                as_of_date=as_of_date,
                reuse=local_handles,
                missing=[],
                newer_revision=[],
                provider_unavailable=True,
                provider_reason=provider_error,
            ),
        )

    # Storage inventory and historical eligibility are distinct responsibilities.
    eligible_remote, future, publication_unknown = [], [], []
    for candidate in remote_candidates:
        qualification = qualify_source(_candidate_filed(candidate), as_of_date=as_of_date)
        if qualification.historical_date_eligible:
            eligible_remote.append(candidate)
        elif qualification.publication_status == "after_as_of":
            future.append(candidate)
        else:
            publication_unknown.append(candidate)

    local_by_year: dict[int, list[Any]] = {}
    for handle in local_handles:
        year = getattr(handle, "fiscal_year", None)
        if year is not None:
            local_by_year.setdefault(year, []).append(handle)

    missing: list[Any] = []
    newer_revision: list[Any] = []
    reuse: list[Any] = []
    remote_by_year: dict[int, list[Any]] = {}
    for candidate in eligible_remote:
        year = _candidate_year(candidate)
        if year is None:
            continue
        remote_by_year.setdefault(year, []).append(candidate)

    for year, locals_here in local_by_year.items():
        remotes_here = remote_by_year.get(year, [])
        if not remotes_here:
            # provider has nothing for this period; local stays reusable
            reuse.extend(locals_here)
            continue
        # same period: prefer the newest accession (amended revisions sort
        # after their base filing)
        newest_remote = max(
            remotes_here,
            key=lambda c: (_candidate_accession(c), _candidate_amended(c)),
        )
        local_accessions = {
            str(getattr(h, "provider_document_id", "") or "") for h in locals_here
        }
        if _candidate_accession(newest_remote) in local_accessions:
            reuse.extend(locals_here)  # local is current
        else:
            newer_revision.append(newest_remote)
            reuse.extend(locals_here)  # old revision stays in provenance

    for year, remotes_here in remote_by_year.items():
        if year not in local_by_year:
            missing.extend(remotes_here)

    # "not_published": as of the as_of_date, the provider has nothing
    # eligible beyond the local latest. A future-dated candidate is excluded
    # from the gap (not yet published by as_of) and does not negate
    # not_published — the local latest IS the latest as of as_of.
    not_published = not missing and not newer_revision and not publication_unknown

    return GapPlan(
        schema_version=GAP_PLAN_SCHEMA_VERSION,
        request_id=request_id,
        as_of_date=as_of_date,
        document_kind=document_kind,
        entity=entity,
        market=market,
        reuse=tuple(reuse),
        missing=tuple(missing),
        newer_revision=tuple(newer_revision),
        not_published=not_published,
        future=tuple(future),
        publication_unknown=tuple(publication_unknown),
        gap_hash=_hash_gap(
            request_id=request_id,
            as_of_date=as_of_date,
            reuse=reuse,
            missing=missing,
            newer_revision=newer_revision,
            provider_unavailable=False,
            provider_reason=None,
            publication_unknown=publication_unknown,
        ),
    )


def _hash_gap(
    *,
    request_id: str,
    as_of_date: str,
    reuse: list[Any],
    missing: list[Any],
    newer_revision: list[Any],
    provider_unavailable: bool,
    provider_reason: str | None,
    publication_unknown: list[Any] | None = None,
) -> str:
    """Deterministic gap hash binding request + local/remote alignment."""
    digest = hashlib.sha256()
    digest.update(request_id.encode())
    digest.update(as_of_date.encode())
    for handle in sorted(
        reuse,
        key=lambda h: (
            str(getattr(h, "fiscal_year", "")),
            str(getattr(h, "provider_document_id", "")),
        ),
    ):
        digest.update(str(getattr(handle, "fiscal_year", "")).encode())
        digest.update(str(getattr(handle, "provider_document_id", "")).encode())
    for candidate in sorted(
        missing + newer_revision,
        key=lambda c: (str(getattr(c, "fiscal_year", "")), _candidate_accession(c)),
    ):
        digest.update(str(getattr(candidate, "fiscal_year", "")).encode())
        digest.update(_candidate_accession(candidate).encode())
    digest.update(b"unavailable" if provider_unavailable else b"ok")
    if provider_reason:
        digest.update(provider_reason.encode())
    for candidate in sorted(publication_unknown or [], key=_candidate_accession):
        digest.update(b"publication_unknown")
        digest.update(_candidate_accession(candidate).encode())
        digest.update(str(_candidate_filed(candidate)).encode())
    return digest.hexdigest()
