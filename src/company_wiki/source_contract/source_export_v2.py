"""Pathless source export; only exact original-text spans are grounded today.

PDF and other parsed documents can carry manifests, but need an immutable,
parser-owned normalized-artifact registry before spans may be exported.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from company_wiki.wire_json import parse_json

from .evidence_span import EVIDENCE_SPAN_SCHEMA_VERSION, EvidenceSpan
from .source_export import SOURCE_EXPORT_ID_PREFIX, SourceExportError
from .source_version import (
    SOURCE_REF_SCHEMA_VERSION, SourceRef, SourceRefError, SourceVersionPort,
    SourceRefMismatchError, VerifiedContent, VerifiedVersionReceipt,
)


SOURCE_EXPORT_V2_SCHEMA_VERSION = "2.0.0"
SOURCE_MANIFEST_V2_SCHEMA_VERSION = "2.0.0"
_BUNDLE_FIELDS = frozenset({
    "schema_version", "source_manifest_schema_version",
    "evidence_span_schema_version", "counts", "manifests",
    "evidence_spans", "bundle_sha256", "export_id",
})
_REF_FIELDS = frozenset({
    "document_id", "source_id", "content_sha256", "byte_size", "mime_type",
})
_MANIFEST_TEXT_FIELDS = frozenset({
    "title", "document_kind", "published_date", "source_url",
    "retrieved_at", "collector_name", "collector_version",
    "canonical_entity_id", "display_name", "market", "security_id",
    "fiscal_period", "period_end", "form_type", "provider",
    "provider_document_id", "language",
})
_MANIFEST_FIELDS = _REF_FIELDS | _MANIFEST_TEXT_FIELDS | {"fiscal_year"}


def _manifest_ref(manifest: object) -> SourceRef:
    """Read the exact source reference from a pathless wire manifest."""
    if not isinstance(manifest, dict) or set(manifest) != _MANIFEST_FIELDS:
        raise SourceExportError("v2 manifest fields are not exact")
    try:
        ref = SourceRef.from_dict({
            "schema_version": SOURCE_REF_SCHEMA_VERSION,
            **{field: manifest[field] for field in _REF_FIELDS},
        })
    except SourceRefError as exc:
        raise SourceExportError(f"invalid v2 manifest identity: {exc}") from exc
    for field in _MANIFEST_TEXT_FIELDS:
        if manifest[field] is not None and not isinstance(manifest[field], str):
            raise SourceExportError(f"invalid v2 manifest {field}")
    year = manifest["fiscal_year"]
    if year is not None and type(year) is not int:
        raise SourceExportError("invalid v2 manifest fiscal_year")
    return ref


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
        and coords.char_end - coords.char_start == len(span.raw_text)
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
        """Decode complete UTF-8 JSON; transport owns actual read budgets."""
        if not isinstance(raw, bytes):
            raise TypeError("v2 bundle must be UTF-8 bytes")

        try:
            parsed = parse_json(raw.decode("utf-8"))
        except (ValueError, RecursionError) as exc:
            raise SourceExportError(f"invalid UTF-8 JSON v2 bundle: {exc}") from exc
        return cls.from_dict(parsed)

    @classmethod
    def build(
        cls,
        *,
        source_reader: SourceVersionPort,
        refs: Sequence[SourceRef],
        evidence_spans: Sequence[EvidenceSpan],
    ) -> SourceExportBundleV2:
        if not isinstance(source_reader, SourceVersionPort):
            raise TypeError("source_reader must implement the verified source port")
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

        refs_by_source: dict[str, SourceRef] = {}
        for ref in refs:
            if ref.source_id in refs_by_source:
                raise SourceExportError("duplicate source_id in v2 export")
            refs_by_source[ref.source_id] = ref

        spans: dict[str, EvidenceSpan] = {}
        spans_by_source: dict[str, list[EvidenceSpan]] = {}
        locators: dict[tuple[str, str], str] = {}
        for span in evidence_spans:
            span_ref = refs_by_source.get(span.source_id)
            if span_ref is None:
                raise SourceExportError("orphan evidence span in v2 export")
            if not _is_groundable_text_shape(span, span_ref.mime_type):
                raise SourceExportError("unverified evidence span in v2 export")
            if span.span_id in spans:
                if spans[span.span_id] != span:
                    raise SourceExportError("conflicting evidence span id")
                continue
            locator_key = (span.source_id, span.locator)
            existing = locators.get(locator_key)
            if existing is not None and existing != span.span_id:
                raise SourceExportError("conflicting evidence locator")
            spans[span.span_id] = span
            locators[locator_key] = span.span_id
            spans_by_source.setdefault(span.source_id, []).append(span)

        manifests: dict[str, dict[str, str | int | None]] = {}
        for ref in refs_by_source.values():
            # The source owner verifies the actual bytes. Ground text one source
            # at a time. Manifest-only sources need no original buffer here.
            source_spans = spans_by_source.get(ref.source_id)
            verified: VerifiedContent | VerifiedVersionReceipt
            if source_spans:
                content = source_reader.open_version(ref, purpose="source_export")
                if not isinstance(content, VerifiedContent):
                    raise SourceExportError("source bytes do not match source ref")
                try:
                    verified = VerifiedContent.verified_observation(content)
                except SourceRefMismatchError as exc:
                    raise SourceExportError("source bytes do not match source ref") from exc
                try:
                    text = verified.data.decode("utf-8")
                except UnicodeDecodeError as exc:
                    raise SourceExportError("unverified evidence span in v2 export") from exc
                for span in source_spans:
                    coords = span.coordinates
                    if text[coords.char_start:coords.char_end] != span.raw_text:
                        raise SourceExportError("unverified evidence span in v2 export")
            else:
                verified = source_reader.verify_version(ref, purpose="source_export")
            if (
                verified.document_id != ref.document_id
                or verified.source_id != ref.source_id
                or verified.content_sha256 != ref.content_sha256
                or verified.byte_size != ref.byte_size
                or verified.schema_version != ref.schema_version
            ):
                raise SourceExportError("source bytes do not match source ref")
            manifest = source_reader.describe_version(ref)
            if _manifest_ref(manifest) != ref:
                raise SourceExportError("v2 manifest does not match verified source ref")
            manifests[ref.source_id] = manifest

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
        source_mimes: dict[str, str] = {}
        for manifest in manifests:
            ref = _manifest_ref(manifest)
            source_mimes[ref.source_id] = ref.mime_type
        if len(manifests) != len(source_mimes) or list(source_mimes) != sorted(source_mimes):
            raise SourceExportError("v2 manifests must be sorted and unique")

        spans = tuple(EvidenceSpan.from_dict(item) for item in spans_raw)
        span_ids = [span.span_id for span in spans]
        if span_ids != sorted(set(span_ids)):
            raise SourceExportError("v2 spans must be sorted and unique")
        if any(span.source_id not in source_mimes for span in spans):
            raise SourceExportError("orphan evidence span in v2 export")
        if any(
            not _is_groundable_text_shape(span, source_mimes[span.source_id])
            for span in spans
        ):
            raise SourceExportError("unverified evidence span in v2 export")
        locators: dict[tuple[str, str], str] = {}
        for span in spans:
            locator_key = (span.source_id, span.locator)
            if locator_key in locators and locators[locator_key] != span.span_id:
                raise SourceExportError("conflicting evidence locator")
            locators[locator_key] = span.span_id

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
