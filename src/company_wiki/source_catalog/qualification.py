"""Pure observations of publication time and verified local source bytes.

These fields grant no access and infer neither publication nor provider use.
An indexed version remains unverified until an existing byte reader proves it.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date


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
    reuse_eligible = date_eligible
    if date_eligible:
        reuse_eligible = (
            None if local_bytes_status == "not_checked"
            else local_bytes_status == "verified"
        )
    return SourceQualification(status, as_of_date, local_bytes_status,
                               date_eligible, reuse_eligible)
