"""Read-side facts for one exact source version (read-only).

Every fact here comes from the frozen read contracts: ``SourceVersionReader``
for identity/period and ``verified_availability_evidence`` for capture proof.
The module never opens a writable connection and never infers a missing value.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from company_wiki.source_catalog.service import SourceCatalog
from company_wiki.source_catalog.source_availability import (
    verified_availability_evidence,
)
from company_wiki.source_catalog.source_reader import (
    SourceReadError,
    SourceRef,
    SourceVersionReader,
)

IDENTITY_FIELDS = (
    "document_kind",
    "canonical_entity_id",
    "market",
    "security_id",
    "form_type",
    "title",
    "language",
)

PERIOD_FIELDS = (
    "fiscal_year",
    "fiscal_period",
    "period_end",
    "published_date",
)


class ReadRefused(Exception):
    """The read side refused to hand out this version, with a named reason."""

    def __init__(self, status: str, reason: str, detail: str = "") -> None:
        super().__init__(f"{status}: {reason}" + (f" ({detail})" if detail else ""))
        self.status = status
        self.reason = reason
        self.detail = detail

    def as_dict(self) -> dict[str, str]:
        return {"status": self.status, "reason": self.reason, "detail": self.detail}


@dataclass(frozen=True)
class SourceRead:
    """What the read side actually produced for one source ref."""

    manifest: dict[str, Any] | None
    data: bytes | None
    availability: dict[str, str] | None
    refusal: ReadRefused | None
    catalog_ref: SourceRef | None

    @property
    def readable(self) -> bool:
        return self.refusal is None


def string_or_none(value: Any) -> str | None:
    """Normalize an observation without inventing a value.

    Empty/whitespace text and non-text scalars are indistinguishable from an
    unknown in the manifest, so both collapse to ``None``.  Integers (the
    manifest's ``fiscal_year``) are preserved as integers.
    """
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value  # type: ignore[return-value]
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return str(value)


def read_source(
    catalog: SourceCatalog,
    ref: SourceRef,
) -> SourceRead:
    """Read one exact version: manifest, verified bytes and capture evidence."""
    reader = SourceVersionReader(catalog)
    catalog_ref: SourceRef | None = None
    manifest: dict[str, Any] | None = None
    data: bytes | None = None
    availability: dict[str, str] | None = None
    try:
        catalog_ref = reader.query_ref(
            ref.document_id, ref.source_id, ref.content_sha256
        )
    except SourceReadError as exc:
        return SourceRead(None, None, None, ReadRefused(exc.status, exc.reason, exc.detail), None)
    except ValueError as exc:
        return SourceRead(
            None, None, None, ReadRefused("blocked", "invalid_request", str(exc)), None
        )
    try:
        opened, manifest = reader.open_described_version(ref)
        data = opened.data
    except SourceReadError as exc:
        # A refusal here is the read side declining to hand out bytes that do
        # not match the requested version.  The availability probe is still
        # meaningful (it reads bounded metadata, not the buffer), so keep it.
        availability = _availability(catalog, ref)
        return SourceRead(
            None, None, availability, ReadRefused(exc.status, exc.reason, exc.detail), catalog_ref
        )
    availability = _availability(catalog, ref)
    return SourceRead(manifest, data, availability, None, catalog_ref)


def _availability(
    catalog: SourceCatalog, ref: SourceRef
) -> dict[str, str] | None:
    try:
        return verified_availability_evidence(catalog, ref)
    except Exception:  # pragma: no cover - the probe only reads bounded metadata
        return None


__all__ = [
    "IDENTITY_FIELDS",
    "PERIOD_FIELDS",
    "ReadRefused",
    "SourceRead",
    "read_source",
    "string_or_none",
]
