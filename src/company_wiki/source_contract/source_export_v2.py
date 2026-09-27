"""Pathless source export; only exact original-text spans are grounded today.

PDF and other parsed documents can carry manifests, but need an immutable,
parser-owned normalized-artifact registry before spans may be exported.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from .evidence_span import EVIDENCE_SPAN_SCHEMA_VERSION, EvidenceSpan
from .source_export import SOURCE_EXPORT_ID_PREFIX, SourceExportError

if TYPE_CHECKING:
    from company_wiki.source_catalog.source_reader import (
        SourceRef,
        SourceVersionReader,
    )


SOURCE_EXPORT_V2_SCHEMA_VERSION = "2.0.0"
SOURCE_MANIFEST_V2_SCHEMA_VERSION = "2.0.0"
_BUNDLE_FIELDS = frozenset({
    "schema_version", "source_manifest_schema_version",
    "evidence_span_schema_version", "counts", "manifests",
    "evidence_spans", "bundle_sha256", "export_id",
})
_MANIFEST_FIELDS = frozenset({
    "document_id", "source_id", "content_sha256", "byte_size", "mime_type",
    "title", "document_kind", "published_date", "source_url",
    "retrieved_at", "collector_name", "collector_version",
    "canonical_entity_id", "display_name", "market", "security_id",
    "fiscal_year", "fiscal_period", "period_end", "form_type", "provider",
    "provider_document_id", "language",
})


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        allow_nan=False,
    )


def _is_groundable_text_shape(span: EvidenceSpan, mime_type: str) -> bool:
    """The wire may claim only coordinates checkable in original UTF-8 text."""
    coords = span.coordinates
    return (
        mime_type == "text/plain"
        and span.raw_text is not None
        and span.structured_value is None
        and coords.char_start is not None
        and coords.char_end is not None
        and all(
            value is None
            for value in (
                coords.page_number, coords.paragraph_index,
                coords.table_index, coords.row_index, coords.column_index,
            )
        )
    )


@dataclass(frozen=True)
class SourceExportBundleV2:
    """Immutable wire snapshot; no consumer receives an original file path."""

    _payload_json: str
    bundle_sha256: str

    @classmethod
    def from_json(cls, raw: bytes) -> SourceExportBundleV2:
        """Parse bounded UTF-8 JSON without duplicate keys or nonfinite numbers."""
        if not isinstance(raw, bytes):
            raise TypeError("v2 bundle must be UTF-8 bytes")
        if len(raw) > 16 * 1024 * 1024:
            raise SourceExportError("v2 bundle exceeds read limit")

        def unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
            result: dict[str, Any] = {}
            for key, value in pairs:
                if key in result:
                    raise SourceExportError("duplicate JSON key in v2 bundle")
                result[key] = value
            return result

        def no_constant(_value: str) -> None:
            raise SourceExportError("nonfinite JSON number in v2 bundle")

        try:
            parsed = json.loads(
                raw.decode("utf-8"),
                object_pairs_hook=unique_pairs,
                parse_constant=no_constant,
            )
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise SourceExportError("invalid UTF-8 JSON v2 bundle") from None
        return cls.from_dict(parsed)

    @classmethod
    def build(
        cls,
        *,
        source_reader: SourceVersionReader,
        refs: Sequence[SourceRef],
        evidence_spans: Sequence[EvidenceSpan],
    ) -> SourceExportBundleV2:
        # source_contract is imported by source_catalog during startup.
        # Importing the reader only when building avoids that package cycle.
        from company_wiki.source_catalog.source_reader import (
            SourceRef,
            SourceVersionReader,
        )

        if not isinstance(source_reader, SourceVersionReader):
            raise TypeError("source_reader must be SourceVersionReader")
        if isinstance(refs, (str, bytes)) or not isinstance(refs, Sequence):
            raise TypeError("refs must be a sequence")
        if isinstance(evidence_spans, (str, bytes)) or not isinstance(
            evidence_spans, Sequence
        ):
            raise TypeError("evidence_spans must be a sequence")
        if not all(isinstance(ref, SourceRef) for ref in refs):
            raise TypeError("refs must contain SourceRef values")
        if not all(isinstance(span, EvidenceSpan) for span in evidence_spans):
            raise TypeError("evidence_spans must contain EvidenceSpan values")

        manifests: dict[str, dict[str, str | int | None]] = {}
        verified_data: dict[str, bytes] = {}
        span_source_ids = {span.source_id for span in evidence_spans}
        for ref in refs:
            if ref.source_id in manifests:
                raise SourceExportError("duplicate source_id in v2 export")
            # A manifest needs an exact-version verification, but no original
            # bytes.  Keep bytes only where original UTF-8 text spans require
            # independent grounding at this boundary.
            content = None
            if ref.source_id in span_source_ids:
                content = source_reader.open_version(ref, purpose="source_export")
                verified = content
            else:
                verified = source_reader.verify_version(
                    ref, purpose="source_export"
                )
            if (
                verified.document_id != ref.document_id
                or verified.source_id != ref.source_id
                or verified.content_sha256 != ref.content_sha256
                or verified.byte_size != ref.byte_size
            ):
                raise SourceExportError("source bytes do not match source ref")
            if content is not None:
                if hashlib.sha256(content.data).hexdigest() != ref.content_sha256:
                    raise SourceExportError("source bytes do not match source ref")
                verified_data[ref.source_id] = content.data
            manifests[ref.source_id] = source_reader.describe_version(ref)

        spans: dict[str, EvidenceSpan] = {}
        locators: dict[tuple[str, str], str] = {}
        decoded_text: dict[str, str] = {}
        for span in evidence_spans:
            if span.source_id not in manifests:
                raise SourceExportError("orphan evidence span in v2 export")
            # A caller can construct a perfectly valid EvidenceSpan for text
            # that was never in the source.  Until normalized parser artifacts
            # have an owned, immutable registry, only exact UTF-8 original-text
            # offsets can be independently grounded at this boundary.
            if not _is_groundable_text_shape(
                span, str(manifests[span.source_id]["mime_type"])
            ):
                raise SourceExportError("unverified evidence span in v2 export")
            coords = span.coordinates
            if span.source_id not in decoded_text:
                try:
                    decoded_text[span.source_id] = verified_data[
                        span.source_id
                    ].decode("utf-8")
                except UnicodeDecodeError:
                    raise SourceExportError(
                        "unverified evidence span in v2 export"
                    ) from None
            if (
                decoded_text[span.source_id][coords.char_start:coords.char_end]
                != span.raw_text
            ):
                raise SourceExportError("unverified evidence span in v2 export")
            if span.span_id in spans and spans[span.span_id] != span:
                raise SourceExportError("conflicting evidence span id")
            locator_key = (span.source_id, span.locator)
            existing = locators.get(locator_key)
            if existing is not None and existing != span.span_id:
                raise SourceExportError("conflicting evidence locator")
            spans[span.span_id] = span
            locators[locator_key] = span.span_id

        payload = {
            "schema_version": SOURCE_EXPORT_V2_SCHEMA_VERSION,
            "source_manifest_schema_version": SOURCE_MANIFEST_V2_SCHEMA_VERSION,
            "evidence_span_schema_version": EVIDENCE_SPAN_SCHEMA_VERSION,
            "counts": {
                "source_manifests": len(manifests),
                "evidence_spans": len(spans),
            },
            "manifests": [manifests[key] for key in sorted(manifests)],
            "evidence_spans": [spans[key].to_dict() for key in sorted(spans)],
        }
        payload_json = _canonical_json(payload)
        digest = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()
        return cls(payload_json, digest)

    @classmethod
    def from_dict(cls, wire: Mapping[str, Any]) -> SourceExportBundleV2:
        """Check v2 wire structure and hash; raw-byte verification is separate."""
        if not isinstance(wire, Mapping):
            raise TypeError("source export input must be an object")
        if set(wire) != _BUNDLE_FIELDS:
            raise SourceExportError("v2 bundle fields are not exact")
        if (
            wire["schema_version"] != SOURCE_EXPORT_V2_SCHEMA_VERSION
            or wire["source_manifest_schema_version"]
            != SOURCE_MANIFEST_V2_SCHEMA_VERSION
            or wire["evidence_span_schema_version"]
            != EVIDENCE_SPAN_SCHEMA_VERSION
        ):
            raise SourceExportError("unsupported v2 contract version")
        manifests = wire["manifests"]
        spans_raw = wire["evidence_spans"]
        if not isinstance(manifests, list) or not isinstance(spans_raw, list):
            raise TypeError("manifests and evidence_spans must be arrays")
        source_ids: list[str] = []
        source_mimes: dict[str, str] = {}
        for manifest in manifests:
            if not isinstance(manifest, dict) or set(manifest) != _MANIFEST_FIELDS:
                raise SourceExportError("v2 manifest fields are not exact")
            for field in ("document_id", "source_id", "content_sha256", "mime_type"):
                if not isinstance(manifest[field], str) or not manifest[field]:
                    raise SourceExportError(f"invalid v2 manifest {field}")
            digest = manifest["content_sha256"]
            if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
                raise SourceExportError("invalid v2 source digest")
            size = manifest["byte_size"]
            if isinstance(size, bool) or not isinstance(size, int) or size < 0:
                raise SourceExportError("invalid v2 source byte_size")
            year = manifest["fiscal_year"]
            if year is not None and (
                isinstance(year, bool) or not isinstance(year, int)
                or year < 1900 or year > 2200
            ):
                raise SourceExportError("invalid v2 fiscal_year")
            for key in _MANIFEST_FIELDS - {
                "document_id", "source_id", "content_sha256", "mime_type",
                "byte_size", "fiscal_year",
            }:
                value = manifest[key]
                if value is not None and not isinstance(value, str):
                    raise SourceExportError(f"invalid v2 manifest {key}")
            source_ids.append(manifest["source_id"])
            source_mimes[manifest["source_id"]] = manifest["mime_type"]
        if source_ids != sorted(set(source_ids)):
            raise SourceExportError("v2 manifests must be sorted and unique")

        spans = tuple(EvidenceSpan.from_dict(item) for item in spans_raw)
        span_ids = [span.span_id for span in spans]
        if span_ids != sorted(set(span_ids)):
            raise SourceExportError("v2 spans must be sorted and unique")
        if any(span.source_id not in source_ids for span in spans):
            raise SourceExportError("orphan evidence span in v2 export")
        if any(
            not _is_groundable_text_shape(span, source_mimes[span.source_id])
            for span in spans
        ):
            raise SourceExportError("unverified evidence span in v2 export")
        locators: dict[tuple[str, str], str] = {}
        for span in spans:
            key = (span.source_id, span.locator)
            if key in locators and locators[key] != span.span_id:
                raise SourceExportError("conflicting evidence locator")
            locators[key] = span.span_id

        counts = wire["counts"]
        if (
            not isinstance(counts, dict)
            or set(counts) != {"source_manifests", "evidence_spans"}
            or any(
                isinstance(value, bool) or not isinstance(value, int) or value < 0
                for value in counts.values()
            )
            or counts["source_manifests"] != len(manifests)
            or counts["evidence_spans"] != len(spans)
        ):
            raise SourceExportError("v2 bundle counts do not match records")
        payload = {key: value for key, value in wire.items()
                   if key not in {"bundle_sha256", "export_id"}}
        payload_json = _canonical_json(payload)
        digest = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()
        if (
            wire["bundle_sha256"] != digest
            or wire["export_id"] != SOURCE_EXPORT_ID_PREFIX + digest
        ):
            raise SourceExportError("v2 bundle identity does not match payload")
        return cls(payload_json, digest)

    def to_dict(self) -> dict[str, Any]:
        payload = json.loads(self._payload_json)
        return {
            **payload,
            "export_id": SOURCE_EXPORT_ID_PREFIX + self.bundle_sha256,
            "bundle_sha256": self.bundle_sha256,
        }
