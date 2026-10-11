"""AUTO's detached native-field view over source-owned official JSON projections.

The source ports verify current parent bytes, layout and issuer/as-of semantics.
This adapter opens one export per operation, preserves each field's true parent
and role, and reuses the existing format-neutral selector. It is not a source
permission, a transcript parser, or a second task store.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
import hashlib
import json
import re
from types import MappingProxyType
from typing import Any, Protocol, cast
import unicodedata

from company_wiki.narrative_subject import NarrativeSubject
from company_wiki.source_catalog.narrative_document import (
    DocumentStructure, NarrativeEvidencePackage, NarrativeUnit,
)
from company_wiki.source_catalog.narrative_evidence import select_narrative_evidence

from .narrative_selector_binding import bind_narrative_selector
from company_wiki.source_catalog.narrative_language import (
    NarrativeLanguageError, detect_narrative_text_language,
)
from company_wiki.source_catalog.official_json_projection import (
    build_projection_export, load_projection,
)
from company_wiki.source_contract import EvidenceCoordinates, EvidenceSpan


NARRATIVE_OFFICIAL_JSON_ADAPTER_VERSION = "1.0.1"

_SHA = re.compile(r"[0-9a-f]{64}\Z")
_PROJECTION_PREFIX = "urn:company-wiki:source-projection:sha256:"
_SOURCE_ROLES = {
    "investor_question": "investor_question",
    "management_answer": "management",
    "company_official_answer": "company_filing",
    "company_statement": "company_filing",
}


class OfficialProjectionAdapterError(ValueError):
    """The compact request or the adapter's finite view cannot be interpreted."""


class ProjectionSelector(Protocol):
    def __call__(self, parsed: DocumentStructure, *, title: str,
                 existing_kind: str = "unknown") -> NarrativeEvidencePackage: ...


def _encoded(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False)


def _hash(value: Any) -> str:
    return hashlib.sha256(_encoded(value).encode("utf-8")).hexdigest()


def _native_fields(export: dict[str, Any]) -> list[tuple[EvidenceSpan, dict[str, Any], dict[str, Any]]]:
    """Join by true parent and pointer; never by lexical proximity or issuer name."""
    records = {(record["parent_content_sha256"], record["record_pointer"]): record
               for record in export["projection"]["records"] if record["selected"]}
    native = []
    for value in export["evidence_spans"]:
        span = EvidenceSpan.from_dict(value)
        binding = span.structured_value
        record = records[(binding["parent_content_sha256"], binding["record_pointer"])]
        fields = {record["record_pointer"] + "/" + item["field"]: item for item in record["fields"]}
        original = fields[binding["pointer"]]
        if original["translation_of"] is not None or original["role"].endswith("_provider_translation"):
            continue
        native.append((span, record, original))
    return native


def _language(native: list[tuple[EvidenceSpan, dict[str, Any], dict[str, Any]]]) -> str | None:
    text = "\n".join(span.raw_text or "" for span, _record, _binding in native)
    if not text.strip():
        return None
    try:
        return detect_narrative_text_language(text)
    except NarrativeLanguageError as exc:
        if exc.code == "SOURCE_LANGUAGE_UNDETERMINED":
            return None
        raise


def _adapted_span(span: EvidenceSpan, record: dict[str, Any], binding: dict[str, Any],
                  *, projection_id: str, language: str | None) -> EvidenceSpan:
    metadata = span.to_dict()["structured_value"]
    role = binding["role"]
    group = "urn:company-wiki:official-json-record:sha256:" + _hash({
        "projection_id": projection_id,
        "parent_content_sha256": record["parent_content_sha256"],
        "record_pointer": record["record_pointer"],
    })
    metadata.update({"original_role": role, "source_role": _SOURCE_ROLES.get(role, "unknown"),
        "language": language, "qa_group_id": group, "official_record_group_id": group,
        "speaker_known": binding["speaker_known"], "source_evidence_id": span.span_id,
        "record_times": record["times"], "record_created_date": record["record_created_date"],
        "as_of_eligibility": record["as_of_eligibility"]})
    # qa_group_id is an association, not a contiguous quote or one mixed-role
    # summary group. selection_group_id is left to the existing selector.
    return EvidenceSpan.create(source_id=span.source_id, coordinates=span.coordinates,
        raw_text=span.raw_text, structured_value=metadata, parser_name=span.parser_name,
        parser_version=span.parser_version, parse_status=span.parse_status,
        quality_flags=span.quality_flags)


@dataclass(frozen=True)
class VerifiedProjectionView:
    """One source-verified operation snapshot; callers receive detached JSON."""
    _export_json: str = field(repr=False)
    subject: NarrativeSubject = field(init=False)
    _spans: tuple[EvidenceSpan, ...] = field(init=False, repr=False)
    _adapter_json: str = field(init=False, repr=False)
    language: str | None = field(init=False)
    coverage_complete: bool = field(init=False)

    def __post_init__(self) -> None:
        try:
            export = self.export_dict()
            _encoded(export)
            value = export["projection"]
            subject = NarrativeSubject.from_dict({
                "kind": "official_json", "item_key": value["projection_id"],
                "subject_sha256": value["projection_sha256"],
                "parent_source_refs": value["parent_source_refs"], "issuer": value["issuer"],
                "as_of_date": value["as_of_date"], "adapter": value["adapter"],
                "coverage": value["coverage"],
            })
            native = _native_fields(export)
            language = _language(native)
            spans = tuple(_adapted_span(span, record, binding,
                projection_id=subject.item_key, language=language)
                for span, record, binding in native)
            coverage = value["coverage"]
            complete = (coverage["page_envelope_complete"] is True
                        and coverage["pagination_complete"] is True)
        except NarrativeLanguageError:
            raise
        except (KeyError, TypeError, ValueError, AttributeError) as exc:
            raise OfficialProjectionAdapterError("invalid_projection_export") from exc
        object.__setattr__(self, "_adapter_json", _encoded(value["adapter"]))
        object.__setattr__(self, "subject", subject)
        object.__setattr__(self, "_spans", spans)
        object.__setattr__(self, "language", language)
        object.__setattr__(self, "coverage_complete", complete)

    def export_dict(self) -> dict[str, Any]:
        """Return the original source export as an independent finite JSON copy."""
        return cast(dict[str, Any], json.loads(self._export_json))

    @property
    def evidence_spans(self) -> tuple[EvidenceSpan, ...]:
        return self._spans

    @property
    def adapter(self) -> dict[str, Any]:
        return cast(dict[str, Any], json.loads(self._adapter_json))


def open_verified_projection(catalog: Any, *, projection_id: str,
                             expected_projection_sha256: str) -> VerifiedProjectionView:
    """Load then export once; source ports own current-byte and semantic checks."""
    if (not isinstance(expected_projection_sha256, str)
            or _SHA.fullmatch(expected_projection_sha256) is None
            or not isinstance(projection_id, str)
            or not projection_id.startswith(_PROJECTION_PREFIX)
            or _SHA.fullmatch(projection_id[len(_PROJECTION_PREFIX):]) is None):
        raise OfficialProjectionAdapterError("invalid_projection_identity")
    projection = load_projection(catalog, projection_id)
    if projection.projection_sha256 != expected_projection_sha256:
        raise OfficialProjectionAdapterError("projection_hash_mismatch")
    exported = build_projection_export(catalog, projection)
    try:
        if (exported["projection"]["projection_id"] != projection_id
                or exported["projection"]["projection_sha256"] != expected_projection_sha256):
            raise OfficialProjectionAdapterError("projection_hash_mismatch")
        return VerifiedProjectionView(_encoded(exported))
    except OfficialProjectionAdapterError:
        raise
    except (TypeError, ValueError, KeyError) as exc:
        raise OfficialProjectionAdapterError("invalid_projection_export") from exc


@dataclass(frozen=True)
class _ProjectionStructure(DocumentStructure):
    _complete: bool = False

    @property
    def coverage_complete(self) -> bool:
        # Native-field count is not proof of full pagination coverage.
        return self._complete


@dataclass(frozen=True)
class _NativeProjectionUnit(NarrativeUnit):
    """Source-export text keeps whitespace; match-only copies remain separate.

    JSON field locators bind the entire decoded field. PDF/TXT normalization's
    trimmed-unit assumption cannot change that displayed source evidence.
    EvidenceSpan v1 still has its source-owned NFC display contract.
    """

    def __post_init__(self) -> None:
        if not self.raw_text.strip() or self.unit_kind != "official_json_field":
            raise ValueError("official field unit must contain native source text")
        if unicodedata.normalize("NFC", self.raw_text) != self.raw_text:
            raise ValueError("official field display text must use NFC")
        if not self.unit_id.startswith("urn:company-wiki:narrative-unit:sha256:"):
            raise ValueError("unit_id must be a canonical narrative-unit SHA-256")
        if not isinstance(self.coordinates, EvidenceCoordinates):
            raise TypeError("coordinates must be EvidenceCoordinates")
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))


def _unit(span: EvidenceSpan) -> NarrativeUnit:
    metadata = span.to_dict()["structured_value"]
    identity = {"evidence_id": span.span_id, "source_id": span.source_id,
                "parser_name": span.parser_name, "parser_version": span.parser_version}
    return _NativeProjectionUnit(unit_id="urn:company-wiki:narrative-unit:sha256:" + _hash(identity),
        source_id=span.source_id, parser_name=span.parser_name, parser_version=span.parser_version,
        coordinates=span.coordinates, raw_text=span.raw_text or "",
        unit_kind="official_json_field", source_role=metadata["source_role"],
        language=metadata["language"], quality_flags=span.quality_flags, metadata=metadata)


def select_verified_projection(view: VerifiedProjectionView, *, title: str,
                               selector: ProjectionSelector = select_narrative_evidence,
                               selector_version: str | None = None
                               ) -> NarrativeEvidencePackage:
    """Reuse the pure selector; package source fields are a real FK anchor only.

    The neutral view.subject remains authoritative item identity. Per-field
    spans keep their actual parents, even when the compatibility package has
    a single real parent anchor. No mixed-role record is joined into one quote.
    """
    bound_selector = bind_narrative_selector(selector, selector_version=selector_version)
    anchor = view.subject.anchor_ref
    native_spans = tuple(span for span in view.evidence_spans if span.raw_text and span.raw_text.strip())
    if view.language is None or not native_spans:
        return NarrativeEvidencePackage(source_id=anchor["source_id"],
            source_sha256=anchor["content_sha256"], document_kind="investor_relations",
            status=("skipped_no_narrative" if view.coverage_complete and not native_spans
                    else "needs_review" if view.coverage_complete else "partial"), evidence_spans=(),
            selection_limit=0, candidate_count=0, dropped_financial_count=0,
            source_units=len(native_spans), omitted_candidate_count=0,
            coverage_complete=view.coverage_complete)
    units = tuple(_unit(span) for span in native_spans)
    parsed = _ProjectionStructure(source_id=anchor["source_id"], source_sha256=anchor["content_sha256"],
        language=view.language, units=units, _complete=view.coverage_complete)
    package = bound_selector(parsed, title=title, existing_kind="investor_relations")
    if not view.coverage_complete and package.status != "blocked":
        return replace(package, coverage_complete=False, status="partial")
    return package


__all__ = ["NARRATIVE_OFFICIAL_JSON_ADAPTER_VERSION",
           "OfficialProjectionAdapterError", "VerifiedProjectionView",
           "open_verified_projection", "select_verified_projection"]
