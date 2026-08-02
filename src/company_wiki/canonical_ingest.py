"""Stateless source-only ingest boundary for canonical upstream contracts."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .source_contract import (
    AnnouncementCollectionReceipt,
    EvidenceCoordinates,
    EvidenceSpan,
    ParseStatus,
    QualityFlag,
    SourceExportBundle,
    SourceManifest,
)


class IngestContractError(ValueError):
    """Raised when an ingest request violates the source-only boundary."""


class IngestSourceMismatchError(IngestContractError):
    """Raised when parser output is attached to a different source."""


def _require_sequence(value: Any, field_name: str) -> Sequence[Any]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise TypeError(f"{field_name} must be a sequence")
    return value


@dataclass(frozen=True)
class ParserResult:
    """One immutable parser output before canonical evidence publication."""

    source_id: str
    coordinates: EvidenceCoordinates
    raw_text: str | None
    structured_value: Any
    parser_name: str
    parser_version: str
    parse_status: ParseStatus | str
    quality_flags: Sequence[QualityFlag | str]

    def __post_init__(self) -> None:
        span = EvidenceSpan.create(
            source_id=self.source_id,
            coordinates=self.coordinates,
            raw_text=self.raw_text,
            structured_value=self.structured_value,
            parser_name=self.parser_name,
            parser_version=self.parser_version,
            parse_status=self.parse_status,
            quality_flags=self.quality_flags,
        )
        object.__setattr__(self, "source_id", span.source_id)
        object.__setattr__(self, "coordinates", span.coordinates)
        object.__setattr__(self, "raw_text", span.raw_text)
        object.__setattr__(self, "structured_value", span.structured_value)
        object.__setattr__(self, "parser_name", span.parser_name)
        object.__setattr__(self, "parser_version", span.parser_version)
        object.__setattr__(self, "parse_status", span.parse_status)
        object.__setattr__(self, "quality_flags", span.quality_flags)

    def to_evidence_span(self) -> EvidenceSpan:
        """Publish this parser output through the versioned evidence contract."""

        return EvidenceSpan.create(
            source_id=self.source_id,
            coordinates=self.coordinates,
            raw_text=self.raw_text,
            structured_value=self.structured_value,
            parser_name=self.parser_name,
            parser_version=self.parser_version,
            parse_status=self.parse_status,
            quality_flags=self.quality_flags,
        )


class IngestService:
    """Verify immutable raw input and publish deterministic source evidence."""

    def __init__(self, *, root: Path):
        if not isinstance(root, Path):
            raise TypeError("root must be pathlib.Path")
        resolved = root.resolve(strict=True)
        if not resolved.is_dir():
            raise IngestContractError("root must be an existing directory")
        self._root = resolved

    def ingest(
        self,
        *,
        manifest: SourceManifest,
        parser_results: Sequence[ParserResult],
        base: SourceExportBundle | None = None,
    ) -> SourceExportBundle:
        """Bind parser results to one manifest and build a read-only export."""

        if not isinstance(manifest, SourceManifest):
            raise TypeError("manifest must be SourceManifest")
        results = _require_sequence(parser_results, "parser_results")
        if not all(isinstance(item, ParserResult) for item in results):
            raise TypeError("parser_results must contain ParserResult values")

        mismatched = sorted(
            {item.source_id for item in results if item.source_id != manifest.source_id}
        )
        if mismatched:
            raise IngestSourceMismatchError(
                "parser result source_id does not match the supplied manifest"
            )

        return SourceExportBundle.build(
            root=self._root,
            manifests=(manifest,),
            evidence_spans=tuple(item.to_evidence_span() for item in results),
            base=base,
        )

    def ingest_announcement(
        self,
        *,
        receipt: AnnouncementCollectionReceipt,
        parser_results: Sequence[ParserResult],
        base: SourceExportBundle | None = None,
    ) -> SourceExportBundle:
        """Validate a canonical announcement receipt and ingest its manifest."""

        if not isinstance(receipt, AnnouncementCollectionReceipt):
            raise TypeError("receipt must be AnnouncementCollectionReceipt")
        validated = AnnouncementCollectionReceipt.from_dict(receipt.to_dict())
        return self.ingest(
            manifest=validated.manifest,
            parser_results=parser_results,
            base=base,
        )


__all__ = [
    "IngestContractError",
    "IngestService",
    "IngestSourceMismatchError",
    "ParserResult",
]
