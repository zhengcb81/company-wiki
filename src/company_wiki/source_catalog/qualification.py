"""Pure observations of publication time and verified local source bytes.

These fields grant no access and infer neither publication nor provider use.
An indexed version remains unverified until an existing byte reader proves it.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
import re


@dataclass(frozen=True)
class SourceQualification:
    publication_status: str
    as_of_date: str | None
    local_bytes_status: str
    historical_date_eligible: bool | None
    historical_reuse_eligible: bool | None
    schema_version: str = "source-qualification/1"

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _iso_date(value: object) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.isoformat() == value else None


def _publication_status(published_date: object, cutoff: date | None) -> str:
    if published_date is None or published_date == "":
        return "unknown"
    published = _iso_date(published_date)
    if published is None:
        return "invalid"
    if cutoff is None:
        return "known"
    return "eligible" if published <= cutoff else "after_as_of"


def qualify_source(
    published_date: object, *, as_of_date: str | None,
    local_bytes_status: str = "not_checked",
    availability_evidence: object = None, source_sha256: str | None = None,
) -> SourceQualification:
    if not isinstance(local_bytes_status, str) or local_bytes_status not in {
        "not_checked", "verified", "unavailable",
    }:
        raise ValueError("local_bytes_status is not a byte verification observation")
    cutoff = _iso_date(as_of_date)
    if as_of_date is not None and cutoff is None:
        raise ValueError("as_of_date must be an exact ISO date")
    status = _publication_status(published_date, cutoff)
    date_eligible = None if cutoff is None else status == "eligible"
    if cutoff is not None and status == "unknown" and isinstance(availability_evidence, dict):
        proof = availability_evidence
        available = _iso_date(proof.get("available_by"))
        if (proof.get("schema_version") == "source-availability-evidence/1"
                and isinstance(source_sha256, str) and re.fullmatch(r"[0-9a-f]{64}", source_sha256)
                and proof.get("source_sha256") == source_sha256
                and proof.get("basis") in {"prior_verified_capture", "primary_archive", "current_verified_open"}
                and all(isinstance(proof.get(k), str) and proof[k].strip() for k in ("evidence_ref", "locator"))
                and available is not None and available <= cutoff):
            date_eligible = True
    reuse_eligible = date_eligible
    if date_eligible:
        reuse_eligible = (
            None if local_bytes_status == "not_checked"
            else local_bytes_status == "verified"
        )
    return SourceQualification(status, as_of_date, local_bytes_status,
                               date_eligible, reuse_eligible)


def latest_source_index(versions: list[dict]) -> int | None:
    """Rank verified fiscal scopes; availability is never a publication date.

    Preserve the known-publication legacy election if scope is not proved.
    A same-period unknown revision cannot be ordered by an accession/mtime.
    """
    if not versions:
        return None
    periods = {"Q1": 1, "H1": 2, "Q2": 2, "Q3": 3, "FY": 4, "Q4": 4}
    keys = [(v.get("fiscal_year"), periods.get(str(v.get("fiscal_period") or ""))) for v in versions]
    proved = all(v.get("scope_verified") and type(key[0]) is int and key[1] is not None
                 for v, key in zip(versions, keys))
    if proved:
        latest = max(keys)
        choices = [i for i, key in enumerate(keys) if key == latest]
    else:
        if any(v.get("scope_verified") for v in versions):
            return 0 if len(versions) == 1 else None
        if any(not v.get("published_date") for v in versions):
            return 0 if len(versions) == 1 else None
        choices = list(range(len(versions)))
    if len(choices) > 1 and any(not versions[i].get("published_date") for i in choices):
        return None
    if proved and len(choices) > 1:
        dates = [str(versions[i].get("published_date") or "") for i in choices]
        newest = max(dates)
        if sum(day == newest for day in dates) > 1:
            return None
    return max(choices, key=lambda i: (versions[i].get("published_date") or "",
                                      versions[i].get("provider_document_id") or "",
                                      versions[i].get("source_id") or ""))
