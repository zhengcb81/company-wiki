"""Strict, pathless contracts for the three narrative automation jobs."""

from __future__ import annotations

import re
import math
from dataclasses import dataclass
from typing import Any, Literal, Mapping, Sequence, cast, overload

from company_wiki.source_catalog.narrative_evidence import (
    SourceSummaryDraft,
    SummaryClaim,
    SummaryValidationError,
    validate_summary_draft,
    validate_summary_claim,
)
from company_wiki.source_contract import EvidenceSpan, source_id_for_sha256
from company_wiki.source_catalog.narrative_language import (
    NarrativeLanguageError,
    narrative_language_family,
)

from company_wiki.narrative_subject import NarrativeSubject, SubjectBindingError

from .models import canonical_json, canonical_json_hash, _freeze_json, _to_plain


SOURCE_REVISION_EVENT_SCHEMA = "source-revision-event/2.0"
PROJECTED_SOURCE_REVISION_EVENT_SCHEMA = "source-revision-event/3.0"
SELECT_RESULT_SCHEMA = "narrative-select-result/2.1"
PROJECTED_SELECT_RESULT_SCHEMA = "narrative-select-result/3.1"
LEGACY_SELECT_RESULT_SCHEMAS = frozenset({
    "narrative-select-result/2.0", "narrative-select-result/3.0",
})
PROJECTED_SELECT_RESULT_SCHEMAS = frozenset({
    "narrative-select-result/3.0", PROJECTED_SELECT_RESULT_SCHEMA,
})
SUPPORTED_SELECT_RESULT_SCHEMAS = frozenset({
    SELECT_RESULT_SCHEMA, PROJECTED_SELECT_RESULT_SCHEMA,
    *LEGACY_SELECT_RESULT_SCHEMAS,
})
SUMMARY_RESULT_SCHEMA = "narrative-summary-result/2.0"
PROJECTED_SUMMARY_RESULT_SCHEMA = "narrative-summary-result/3.0"
BUNDLE_SCHEMA = "narrative-bundle/2.0"
PROJECTED_BUNDLE_SCHEMA = "narrative-bundle/3.0"
ASSESSED_BUNDLE_SCHEMA = "narrative-bundle/2.1"
ASSESSED_PROJECTED_BUNDLE_SCHEMA = "narrative-bundle/3.1"
SELECT_RESULT_MAX_BYTES = 1024 * 1024
SUMMARY_RESULT_MAX_BYTES = 64 * 1024
BUNDLE_MAX_BYTES = 1280 * 1024
SKIP_BUNDLE_MAX_BYTES = 16 * 1024
READING_CONTEXT_MAX_BYTES = 192 * 1024

_SHA = re.compile(r"[0-9a-f]{64}\Z")
_DRIVE_PATH = re.compile(r"[A-Za-z]:[\\/]")
_NARRATIVE_UNIT_ID = re.compile(r"urn:company-wiki:narrative-unit:sha256:[0-9a-f]{64}\Z")
_READING_GROUP_ID = re.compile(r"urn:company-wiki:reading-group:sha256:[0-9a-f]{64}\Z")
_READING_PACKAGE_ID = re.compile(r"urn:company-wiki:reading-package:sha256:[0-9a-f]{64}\Z")
_EVIDENCE_SPAN_ID = re.compile(r"urn:company-wiki:evidence-span:sha256:[0-9a-f]{64}\Z")
_LOCATOR = re.compile(
    r"loc:v1(?:/(?:page|paragraph|table|row|column):[0-9]+)*"
    r"(?:/chars:[0-9]+-[0-9]+)?\Z"
)
_DOCUMENT_WORK_DETAIL = "unexamined source content remains unknown; original is unchanged"
_TRACE_CODE = re.compile(r"[A-Za-z][A-Za-z0-9_-]{0,79}\Z")
_PATH_KEYS = frozenset(
    {
        "path",
        "absolute_path",
        "local_path",
        "file_path",
        "root_path",
        "wiki_root",
        "catalog_path",
    }
)
_LANGUAGES = frozenset({"zh", "en", "mixed"})
_SOURCE_CLASSES = frozenset({"filing", "transcript"})
_SELECTION_STATUSES = frozenset(
    {"selected", "partial", "skipped_no_narrative", "needs_review", "blocked"}
)
_QUALITY_STATUSES = frozenset({"verified", "needs_review", "skipped_no_narrative"})
_REVIEW_STATUSES = frozenset({"not_detected", "detected_and_ignored", "not_reviewed"})


class NarrativeContractError(ValueError):
    """A narrative job payload differs from the frozen contract."""


class ContractSizeError(NarrativeContractError):
    """A canonical payload exceeds its persisted byte budget."""


class PhysicalPathLeakError(NarrativeContractError):
    """A physical filesystem location crossed the job contract."""


def _object(value: object, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise NarrativeContractError(f"{name} must be an object")
    return value


def _exact(value: object, keys: set[str], name: str) -> Mapping[str, Any]:
    item = _object(value, name)
    supplied = set(item)
    unknown = supplied - keys
    missing = keys - supplied
    if unknown:
        raise NarrativeContractError(f"{name} unknown fields: {sorted(unknown)}")
    if missing:
        raise NarrativeContractError(f"{name} missing fields: {sorted(missing)}")
    return item


@overload
def _text(value: object, name: str, *, optional: Literal[False] = False) -> str: ...


@overload
def _text(value: object, name: str, *, optional: Literal[True]) -> str | None: ...


def _text(value: object, name: str, *, optional: bool = False) -> str | None:
    if optional and value is None:
        return None
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise NarrativeContractError(f"{name} must be non-empty trimmed text")
    return value


@overload
def _sha(value: object, name: str, *, optional: Literal[False] = False) -> str: ...


@overload
def _sha(value: object, name: str, *, optional: Literal[True]) -> str | None: ...


def _sha(value: object, name: str, *, optional: bool = False) -> str | None:
    if optional and value is None:
        return None
    if not isinstance(value, str) or not _SHA.fullmatch(value):
        raise NarrativeContractError(f"{name} must be lowercase SHA-256")
    return value


def _integer(value: object, name: str, *, positive: bool = False) -> int:
    if type(value) is not int or value < (1 if positive else 0):
        relation = "positive" if positive else "non-negative"
        raise NarrativeContractError(f"{name} must be a {relation} integer")
    return value


def _array(value: object, name: str) -> Sequence[Any]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise NarrativeContractError(f"{name} must be an array")
    return value


def _looks_like_path(value: str) -> bool:
    return bool(
        _DRIVE_PATH.match(value)
        or value.startswith("\\\\")
        or value.lower().startswith("file://")
    )


def assert_no_physical_paths(value: object) -> None:
    """Reject filesystem locations recursively while allowing source locators."""
    if isinstance(value, Mapping):
        for key, child in value.items():
            if not isinstance(key, str):
                raise NarrativeContractError("JSON object keys must be strings")
            if key.lower() in _PATH_KEYS:
                raise PhysicalPathLeakError(f"physical path field is forbidden: {key}")
            assert_no_physical_paths(child)
        return
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for child in value:
            assert_no_physical_paths(child)
        return
    if isinstance(value, str) and _looks_like_path(value):
        raise PhysicalPathLeakError("physical path value is forbidden")


def _encoded_size(value: Mapping[str, Any]) -> int:
    assert_no_physical_paths(value)
    return len(canonical_json(value).encode("utf-8"))


def _enforce_cap(value: Mapping[str, Any], cap: int, name: str) -> int:
    size = _encoded_size(value)
    if size > cap:
        raise ContractSizeError(f"{name} result exceeds {cap} bytes")
    return size


@dataclass(frozen=True)
class SourceRefValue:
    schema_version: str
    document_id: str
    source_id: str
    content_sha256: str
    byte_size: int
    mime_type: str

    @classmethod
    def from_dict(cls, value: object) -> "SourceRefValue":
        item = _exact(
            value,
            {
                "schema_version",
                "document_id",
                "source_id",
                "content_sha256",
                "byte_size",
                "mime_type",
            },
            "source_ref",
        )
        schema = _text(item["schema_version"], "source_ref.schema_version")
        if schema != "2.0":
            raise NarrativeContractError("unsupported source_ref schema")
        digest = _sha(item["content_sha256"], "source_ref.content_sha256")
        source_id = _text(item["source_id"], "source_ref.source_id")
        if source_id != source_id_for_sha256(digest):
            raise NarrativeContractError(
                "source_ref.source_id does not match content hash"
            )
        return cls(
            schema,
            _text(item["document_id"], "source_ref.document_id"),
            source_id,
            digest,
            _integer(item["byte_size"], "source_ref.byte_size", positive=True),
            _text(item["mime_type"], "source_ref.mime_type"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "document_id": self.document_id,
            "source_id": self.source_id,
            "content_sha256": self.content_sha256,
            "byte_size": self.byte_size,
            "mime_type": self.mime_type,
        }


@dataclass(frozen=True)
class SourceMetadataValue:
    source_class: str
    title: str | None
    document_kind: str
    language: str
    declared_language: str | None = None

    @classmethod
    def from_dict(
        cls, value: object, *, projected: bool = False
    ) -> "SourceMetadataValue":
        item = _exact(
            value,
            {"source_class", "title", "document_kind", "language"}
            | (
                {"declared_language"}
                if isinstance(value, Mapping) and "declared_language" in value
                else set()
            ),
            "source_metadata",
        )
        source_class = _text(item["source_class"], "source_metadata.source_class")
        classes = {"official_json"} if projected else _SOURCE_CLASSES
        if source_class not in classes:
            raise NarrativeContractError("source_metadata.source_class is invalid")
        language = _text(item["language"], "source_metadata.language")
        if language not in (_LANGUAGES | {"unknown"} if projected else _LANGUAGES):
            raise NarrativeContractError("source_metadata.language is invalid")
        declared = _text(
            item.get("declared_language"),
            "source_metadata.declared_language",
            optional=True,
        )
        if declared is not None:
            try:
                family = narrative_language_family(declared)
            except NarrativeLanguageError as exc:
                raise NarrativeContractError(
                    "source_metadata.declared_language is invalid"
                ) from exc
            if family != language:
                raise NarrativeContractError(
                    "source_metadata.language does not match declared_language"
                )
        return cls(
            source_class,
            _text(item["title"], "source_metadata.title", optional=True),
            _text(item["document_kind"], "source_metadata.document_kind"),
            language,
            declared,
        )

    def to_dict(self) -> dict[str, Any]:
        result = {
            "source_class": self.source_class,
            "title": self.title,
            "document_kind": self.document_kind,
            "language": self.language,
        }
        if self.declared_language is not None:
            result["declared_language"] = self.declared_language
        return result


@dataclass(frozen=True)
class SourceRevisionEventPayload:
    schema_version: str
    source_ref: SourceRefValue  # Real FK anchor; public projection DTO never labels it as the subject.
    expected_read_policy_sha256: str | None
    source_metadata: SourceMetadataValue
    subject_binding: NarrativeSubject | None = None

    @classmethod
    def from_dict(cls, value: object) -> "SourceRevisionEventPayload":
        assert_no_physical_paths(value)
        if (
            isinstance(value, Mapping)
            and value.get("schema_version") == PROJECTED_SOURCE_REVISION_EVENT_SCHEMA
        ):
            item = _exact(
                value,
                {"schema_version", "subject_binding", "source_metadata"},
                "source projection event",
            )
            try:
                subject = NarrativeSubject.from_dict(item["subject_binding"])
            except SubjectBindingError as exc:
                raise NarrativeContractError(
                    "invalid source projection subject"
                ) from exc
            if subject.kind != "official_json":
                raise NarrativeContractError(
                    "projection event requires projection subject"
                )
            return cls(
                PROJECTED_SOURCE_REVISION_EVENT_SCHEMA,
                SourceRefValue.from_dict(subject.anchor_ref),
                None,
                SourceMetadataValue.from_dict(item["source_metadata"], projected=True),
                subject,
            )
        item = _exact(
            value,
            {
                "schema_version",
                "source_ref",
                "expected_read_policy_sha256",
                "source_metadata",
            },
            "source revision event",
        )
        if item["schema_version"] != SOURCE_REVISION_EVENT_SCHEMA:
            raise NarrativeContractError("unsupported source revision event schema")
        return cls(
            SOURCE_REVISION_EVENT_SCHEMA,
            SourceRefValue.from_dict(item["source_ref"]),
            _sha(item["expected_read_policy_sha256"], "expected_read_policy_sha256"),
            SourceMetadataValue.from_dict(item["source_metadata"]),
        )

    @property
    def subject(self) -> NarrativeSubject:
        return self.subject_binding or NarrativeSubject.from_raw(
            self.source_ref.to_dict()
        )

    @property
    def item_key(self) -> str:
        return (
            self.subject_binding.item_key
            if self.subject_binding is not None
            else self.source_ref.document_id
        )

    @property
    def input_hash(self) -> str:
        return cast(str, canonical_json_hash(self.to_dict()))

    def to_dict(self) -> dict[str, Any]:
        if self.subject_binding is not None:
            return {
                "schema_version": self.schema_version,
                "subject_binding": self.subject_binding.to_dict(),
                "source_metadata": self.source_metadata.to_dict(),
            }
        return {
            "schema_version": self.schema_version,
            "source_ref": self.source_ref.to_dict(),
            "expected_read_policy_sha256": self.expected_read_policy_sha256,
            "source_metadata": self.source_metadata.to_dict(),
        }


@dataclass(frozen=True)
class PromptReviewValue:
    status: str
    source_sha256: str | None
    evidence_sha256: str | None
    policy_hash: str | None
    reviewed_at: str | None

    @classmethod
    def from_dict(cls, value: object) -> "PromptReviewValue":
        item = _exact(
            value,
            {
                "status",
                "source_sha256",
                "evidence_sha256",
                "policy_hash",
                "reviewed_at",
            },
            "prompt_review",
        )
        status = _text(item["status"], "prompt_review.status")
        if status not in _REVIEW_STATUSES:
            raise NarrativeContractError("prompt_review.status is invalid")
        fields = (
            _sha(item["source_sha256"], "prompt_review.source_sha256", optional=True),
            _sha(
                item["evidence_sha256"], "prompt_review.evidence_sha256", optional=True
            ),
            _sha(item["policy_hash"], "prompt_review.policy_hash", optional=True),
            _text(item["reviewed_at"], "prompt_review.reviewed_at", optional=True),
        )
        if status == "not_reviewed" and any(part is not None for part in fields):
            raise NarrativeContractError(
                "not_reviewed prompt_review must have null bindings"
            )
        if status != "not_reviewed" and any(part is None for part in fields):
            raise NarrativeContractError(
                "reviewed prompt_review requires complete bindings"
            )
        return cls(status, *fields)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "source_sha256": self.source_sha256,
            "evidence_sha256": self.evidence_sha256,
            "policy_hash": self.policy_hash,
            "reviewed_at": self.reviewed_at,
        }

    def validate_source(self, source: SourceRefValue) -> None:
        if (
            self.status != "not_reviewed"
            and self.source_sha256 != source.content_sha256
        ):
            raise NarrativeContractError(
                "prompt_review source hash differs from source_ref"
            )


@dataclass(frozen=True)
class ComponentValue:
    name: str
    version: str

    @classmethod
    def from_dict(cls, value: object, name: str) -> "ComponentValue":
        item = _exact(value, {"name", "version"}, name)
        return cls(
            _text(item["name"], f"{name}.name"),
            _text(item["version"], f"{name}.version"),
        )

    def to_dict(self) -> dict[str, str]:
        return {"name": self.name, "version": self.version}


@dataclass(frozen=True)
class SelectionValue:
    status: str
    coverage_complete: bool
    source_units: int
    candidate_count: int
    selected_count: int
    omitted_candidate_count: int
    dropped_financial_count: int
    pages_total: int
    pages_read: int
    lines_total: int
    tables_total: int
    tables_scanned: int

    @classmethod
    def from_dict(cls, value: object) -> "SelectionValue":
        keys = {
            "status",
            "coverage_complete",
            "source_units",
            "candidate_count",
            "selected_count",
            "omitted_candidate_count",
            "dropped_financial_count",
            "pages_total",
            "pages_read",
            "lines_total",
            "tables_total",
            "tables_scanned",
        }
        item = _exact(value, keys, "selection")
        status = _text(item["status"], "selection.status")
        if status not in _SELECTION_STATUSES:
            raise NarrativeContractError("selection.status is invalid")
        if type(item["coverage_complete"]) is not bool:
            raise NarrativeContractError("selection.coverage_complete must be boolean")
        result = cls(
            status=status,
            coverage_complete=item["coverage_complete"],
            source_units=_integer(item["source_units"], "selection.source_units"),
            candidate_count=_integer(
                item["candidate_count"], "selection.candidate_count"
            ),
            selected_count=_integer(item["selected_count"], "selection.selected_count"),
            omitted_candidate_count=_integer(
                item["omitted_candidate_count"], "selection.omitted_candidate_count"
            ),
            dropped_financial_count=_integer(
                item["dropped_financial_count"], "selection.dropped_financial_count"
            ),
            pages_total=_integer(item["pages_total"], "selection.pages_total"),
            pages_read=_integer(item["pages_read"], "selection.pages_read"),
            lines_total=_integer(item["lines_total"], "selection.lines_total"),
            tables_total=_integer(item["tables_total"], "selection.tables_total"),
            tables_scanned=_integer(item["tables_scanned"], "selection.tables_scanned"),
        )
        if (
            result.pages_read > result.pages_total
            or result.tables_scanned > result.tables_total
        ):
            raise NarrativeContractError("selection scan counters exceed totals")
        if result.selected_count > result.candidate_count:
            raise NarrativeContractError("selection selected_count exceeds candidates")
        return result

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "coverage_complete": self.coverage_complete,
            "source_units": self.source_units,
            "candidate_count": self.candidate_count,
            "selected_count": self.selected_count,
            "omitted_candidate_count": self.omitted_candidate_count,
            "dropped_financial_count": self.dropped_financial_count,
            "pages_total": self.pages_total,
            "pages_read": self.pages_read,
            "lines_total": self.lines_total,
            "tables_total": self.tables_total,
            "tables_scanned": self.tables_scanned,
        }


def _evidence(value: object) -> tuple[EvidenceSpan, ...]:
    spans = tuple(
        EvidenceSpan.from_dict(item) for item in _array(value, "evidence_spans")
    )
    ids = [span.span_id for span in spans]
    if len(ids) != len(set(ids)):
        raise NarrativeContractError("evidence_spans contain duplicate IDs")
    return spans


@dataclass(frozen=True)
class TranscriptLineageValue:
    values: Mapping[str, Any]

    @classmethod
    def from_dict(cls, value: object) -> "TranscriptLineageValue":
        keys = {
            "schema_version",
            "original_source_id",
            "original_sha256",
            "original_mime_type",
            "original_byte_size",
            "text_sha256",
            "text_byte_size",
            "extractor_version",
            "line_count",
        }
        item = _exact(value, keys, "transcript_lineage")
        checked = dict(item)
        if checked["schema_version"] != "transcript-material/2":
            raise NarrativeContractError("unsupported transcript lineage schema")
        for key in ("original_source_id", "original_mime_type", "extractor_version"):
            checked[key] = _text(checked[key], f"transcript_lineage.{key}")
        for key in ("original_sha256", "text_sha256"):
            checked[key] = _sha(checked[key], f"transcript_lineage.{key}")
        for key in ("original_byte_size", "text_byte_size", "line_count"):
            checked[key] = _integer(
                checked[key], f"transcript_lineage.{key}", positive=True
            )
        return cls(checked)

    def to_dict(self) -> dict[str, Any]:
        return dict(self.values)


@dataclass(frozen=True)
class TranscriptByteBinding:
    evidence_id: str
    material_line_start: int
    material_line_end: int
    source_byte_ranges: tuple[tuple[int, int], ...]

    @classmethod
    def from_dict(cls, value: object) -> "TranscriptByteBinding":
        item = _exact(
            value,
            {
                "evidence_id",
                "material_line_start",
                "material_line_end",
                "source_byte_ranges",
            },
            "transcript byte binding",
        )
        start = _integer(
            item["material_line_start"], "material_line_start", positive=True
        )
        end = _integer(item["material_line_end"], "material_line_end", positive=True)
        if end < start:
            raise NarrativeContractError("transcript material line range is invalid")
        ranges: list[tuple[int, int]] = []
        for raw in _array(item["source_byte_ranges"], "source_byte_ranges"):
            pair = _exact(raw, {"start", "end"}, "source byte range")
            byte_start = _integer(pair["start"], "source byte start")
            byte_end = _integer(pair["end"], "source byte end", positive=True)
            if byte_end <= byte_start:
                raise NarrativeContractError("source byte range is invalid")
            ranges.append((byte_start, byte_end))
        if not ranges:
            raise NarrativeContractError("source_byte_ranges must not be empty")
        return cls(_text(item["evidence_id"], "evidence_id"), start, end, tuple(ranges))

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "material_line_start": self.material_line_start,
            "material_line_end": self.material_line_end,
            "source_byte_ranges": [
                {"start": start, "end": end} for start, end in self.source_byte_ranges
            ],
        }


def _projection_subject(value: object) -> NarrativeSubject:
    try:
        subject = NarrativeSubject.from_dict(value)
    except SubjectBindingError as exc:
        raise NarrativeContractError("invalid projection subject binding") from exc
    if subject.kind != "official_json":
        raise NarrativeContractError("projection schema requires projection subject")
    return subject


def _validate_projection_evidence(
    subject: NarrativeSubject, spans: Sequence[EvidenceSpan], selection: SelectionValue
) -> None:
    parents = {
        (ref["source_id"], ref["content_sha256"]) for ref in subject.parent_source_refs
    }
    for span in spans:
        binding = span.structured_value
        if (
            span.source_id,
            binding.get("parent_content_sha256"),
        ) not in parents or binding.get("projection_id") != subject.item_key:
            raise NarrativeContractError(
                "selected evidence differs from projection parents or identity"
            )
    coverage = subject.to_dict()["coverage"]
    if selection.coverage_complete and not (
        coverage.get("pagination_complete") is True
        and coverage.get("page_envelope_complete") is True
    ):
        raise NarrativeContractError(
            "selection cannot promote partial projection coverage"
        )


def _subject_wire(
    value: dict[str, Any], subject: NarrativeSubject | None, *, remove: Sequence[str]
) -> dict[str, Any]:
    if subject is not None:
        for key in remove:
            value.pop(key, None)
        value["subject_binding"] = subject.to_dict()
    return value


_READING_POLICY_KEYS = {
    "profile_id", "profile_version", "family", "summary_focus", "policy_components",
    "reading_questions", "context_requirements", "family_policy", "negative_hints",
    "semantic_units", "section_priorities",
}
_READING_FACET_KEYS = {
    "id", "version", "content_digest", "selection_basis", "business_questions",
    "summary_focus", "required_context", "absence_rules", "confusion_checks",
    "applicable_mechanisms",
}
_READING_FORBIDDEN_KEYS = {
    "raw_text", "body", "observation", "evidence_packages", "members",
    "wrong_assertion", "correct_assertion", "source_meaning", "confusions", "examples", "example",
}


def _assert_pathless_reading_wire(value: object) -> None:
    # The optional context has its own bounded walk below. Walking it here
    # first would defeat that bound for deeply nested untrusted wire data.
    if isinstance(value, Mapping) and ({"reading_context", "reading_dependencies"} & value.keys()):
        assert_no_physical_paths({key: child for key, child in value.items()
                                  if key not in {"reading_context", "reading_dependencies"}})
    else:
        assert_no_physical_paths(value)


def _bounded_reading_json(value: object) -> Any:
    """Detach finite policy data before recursion, storage and model projection.

    This checks the transport shape, never selects policies or reads sources.
    The shared reading engine owns their content and causal decision identity.
    """
    remaining = 30_000

    def visit(item: object, depth: int) -> Any:
        nonlocal remaining
        remaining -= 1
        if remaining < 0 or depth > 12:
            raise NarrativeContractError("reading_context structural bound exceeded")
        if item is None or type(item) is bool or type(item) is int:
            return item
        if type(item) is float:
            if not math.isfinite(item):
                raise NarrativeContractError("reading_context numbers must be finite")
            return item
        if isinstance(item, str):
            if len(item) > 16_384:
                raise NarrativeContractError("reading_context text bound exceeded")
            return item
        if isinstance(item, Mapping):
            if len(item) > 256:
                raise NarrativeContractError("reading_context object bound exceeded")
            result = {}
            for key, child in item.items():
                if not isinstance(key, str) or len(key) > 128:
                    raise NarrativeContractError("reading_context key is invalid")
                if key in _READING_FORBIDDEN_KEYS:
                    raise NarrativeContractError(f"reading_context forbidden field: {key}")
                result[key] = visit(child, depth + 1)
            return result
        if isinstance(item, Sequence) and not isinstance(item, (str, bytes)):
            if len(item) > 4096:
                raise NarrativeContractError("reading_context array bound exceeded")
            return [visit(child, depth + 1) for child in item]
        raise NarrativeContractError("reading_context must contain JSON data only")

    return visit(value, 0)


def _reading_texts(value: object, name: str, *, limit: int = 4096) -> Sequence[Any]:
    rows = _array(value, name)
    if len(rows) > limit:
        raise NarrativeContractError(f"{name} array bound exceeded")
    for row in rows:
        _text(row, name)
    return rows


def _selection_diagnostic_target(value: object, *, code: str) -> Mapping[str, Any]:
    item = _exact(value, {
        "item_id", "item_ids", "item_count", "item_ids_limited", "group_id",
        "locator", "used", "requested", "limit", "closure_size",
    }, "selection_diagnostic.target")
    item_id = _text(item["item_id"], "selection_diagnostic.target.item_id")
    if not _NARRATIVE_UNIT_ID.fullmatch(item_id):
        raise NarrativeContractError("selection_diagnostic target ID is invalid")
    item_ids = _array(item["item_ids"], "selection_diagnostic.target.item_ids")
    if len(item_ids) > 16:
        raise NarrativeContractError("selection_diagnostic target ID sample exceeds its bound")
    for item_id in item_ids:
        checked_id = _text(item_id, "selection_diagnostic.target.item_id")
        if not _NARRATIVE_UNIT_ID.fullmatch(checked_id):
            raise NarrativeContractError("selection_diagnostic target ID is invalid")
    item_count = _integer(item["item_count"], "selection_diagnostic.target.item_count", positive=True)
    if item_count < len(item_ids) or type(item["item_ids_limited"]) is not bool:
        raise NarrativeContractError("selection_diagnostic target ID sample is inconsistent")
    if item["item_ids_limited"] != (item_count > len(item_ids)):
        raise NarrativeContractError("selection_diagnostic target ID limitation is inconsistent")
    group_id = item["group_id"]
    if group_id is not None and not _READING_GROUP_ID.fullmatch(
        _text(group_id, "selection_diagnostic.target.group_id")
    ):
        raise NarrativeContractError("selection_diagnostic target group ID is invalid")
    locator = item["locator"]
    if (not isinstance(locator, str) or not _LOCATOR.fullmatch(locator)
            or locator != locator.strip() or len(locator) > 512):
        raise NarrativeContractError("selection_diagnostic target locator is invalid")
    used = _integer(item["used"], "selection_diagnostic.target.used")
    requested = _integer(item["requested"], "selection_diagnostic.target.requested", positive=True)
    limit = _integer(item["limit"], "selection_diagnostic.target.limit",
                     positive=code != "character_budget")
    closure_size = _integer(item["closure_size"], "selection_diagnostic.target.closure_size", positive=True)
    if used > limit:
        raise NarrativeContractError("selection_diagnostic target used exceeds its limit")
    if used + requested <= limit:
        raise NarrativeContractError("selection_diagnostic target does not exceed its limit")
    if code == "group_exceeds_limit" and closure_size <= limit:
        raise NarrativeContractError("selection_diagnostic closure does not exceed its span limit")
    return item


def _selection_diagnostic(value: object) -> Mapping[str, Any]:
    item = _object(value, "selection_diagnostic")
    required = {"code", "count"}
    allowed = required | {
        "phase", "external_model_cost", "dimension", "used", "requested", "limit", "detail",
        "targets", "targets_limited", "max_closure_size",
    }
    unknown = set(item) - allowed
    missing = required - set(item)
    if unknown:
        raise NarrativeContractError(f"selection_diagnostic unknown fields: {sorted(unknown)}")
    if missing:
        raise NarrativeContractError(f"selection_diagnostic missing fields: {sorted(missing)}")
    code = _text(item["code"], "selection_diagnostic.code")
    if len(code) > 80:
        raise NarrativeContractError("selection_diagnostic.code is too long")
    _integer(item["count"], "selection_diagnostic.count", positive=True)

    if set(item) == required:
        if code != "DECISION_DEPENDENCIES_UNAVAILABLE":
            raise NarrativeContractError("selection_diagnostic without dimension is unsupported")
        return item

    _text(item.get("phase"), "selection_diagnostic.phase")
    if len(item["phase"]) > 80:
        raise NarrativeContractError("selection_diagnostic.phase is too long")
    if item.get("external_model_cost") is not False:
        raise NarrativeContractError("selection_diagnostic.external_model_cost must be false")
    dimension = _text(item.get("dimension"), "selection_diagnostic.dimension")
    if len(dimension) > 80:
        raise NarrativeContractError("selection_diagnostic.dimension is too long")
    combinations = {
        "budget_full": "selection_spans",
        "group_exceeds_limit": "selection_spans",
        "character_budget": "selection_characters",
        "work_budget_exhausted": {"selection_work", "document_work"},
        "missing_required_context": "selection_policy",
    }
    expected_dimension = combinations.get(code)
    if expected_dimension is None or dimension not in (
        expected_dimension if isinstance(expected_dimension, set) else {expected_dimension}
    ):
        raise NarrativeContractError("selection_diagnostic code and dimension do not match")

    metric_keys = {"used", "requested", "limit", "detail"}
    if code in {"budget_full", "character_budget"}:
        base = required | {"phase", "external_model_cost", "dimension", "used", "limit"}
        enriched = base | {"targets", "targets_limited"}
        if frozenset(item) not in {frozenset(base), frozenset(enriched)}:
            raise NarrativeContractError("selection_diagnostic budget fields differ from its dimension")
        used = _integer(item["used"], "selection_diagnostic.used")
        limit = _integer(item["limit"], "selection_diagnostic.limit",
                         positive=code != "character_budget")
        if used > limit:
            raise NarrativeContractError("selection_diagnostic used exceeds limit")
        if set(item) == enriched:
            targets = _array(item["targets"], "selection_diagnostic.targets")
            if len(targets) > 32 or type(item["targets_limited"]) is not bool:
                raise NarrativeContractError("selection_diagnostic target sample is invalid")
            if len(targets) > item["count"]:
                raise NarrativeContractError("selection_diagnostic target sample exceeds its count")
            if item["targets_limited"] != (item["count"] > len(targets)):
                raise NarrativeContractError("selection_diagnostic target sample count is inconsistent")
            for target in targets:
                checked_target = _selection_diagnostic_target(target, code=code)
                if checked_target["limit"] != limit:
                    raise NarrativeContractError("selection_diagnostic target limit differs from its parent")
    elif dimension == "document_work":
        expected = required | {"phase", "external_model_cost", "dimension", *metric_keys}
        if set(item) != expected:
            raise NarrativeContractError("selection_diagnostic work fields differ from its dimension")
        _integer(item["used"], "selection_diagnostic.used")
        limit = _integer(item["limit"], "selection_diagnostic.limit")
        if item["used"] > limit:
            raise NarrativeContractError("selection_diagnostic used exceeds limit")
        if item["requested"] is not None:
            _integer(item["requested"], "selection_diagnostic.requested")
        detail = _text(item["detail"], "selection_diagnostic.detail")
        if detail != _DOCUMENT_WORK_DETAIL:
            raise NarrativeContractError("selection_diagnostic.detail is not the fixed safe message")
    elif code == "group_exceeds_limit":
        legacy = required | {"phase", "external_model_cost", "dimension"}
        enriched = legacy | {"limit", "max_closure_size", "targets", "targets_limited"}
        if frozenset(item) not in {frozenset(legacy), frozenset(enriched)}:
            raise NarrativeContractError("selection_diagnostic policy fields differ from its dimension")
        if set(item) == enriched:
            limit = _integer(item["limit"], "selection_diagnostic.limit", positive=True)
            closure_size = _integer(item["max_closure_size"], "selection_diagnostic.max_closure_size", positive=True)
            if closure_size <= limit:
                raise NarrativeContractError("selection_diagnostic maximum closure does not exceed its limit")
            targets = _array(item["targets"], "selection_diagnostic.targets")
            if len(targets) > 32 or type(item["targets_limited"]) is not bool:
                raise NarrativeContractError("selection_diagnostic target sample is invalid")
            if len(targets) > item["count"]:
                raise NarrativeContractError("selection_diagnostic target sample exceeds its count")
            if item["targets_limited"] != (item["count"] > len(targets)):
                raise NarrativeContractError("selection_diagnostic target sample count is inconsistent")
            checked_targets = [_selection_diagnostic_target(target, code=code) for target in targets]
            if any(target["limit"] != limit for target in checked_targets):
                raise NarrativeContractError("selection_diagnostic target limit differs from its parent")
            if any(target["closure_size"] > closure_size for target in checked_targets):
                raise NarrativeContractError("selection_diagnostic maximum closure size is inconsistent")
    elif code in {"work_budget_exhausted", "missing_required_context"}:
        expected = required | {"phase", "external_model_cost", "dimension"}
        if set(item) != expected:
            raise NarrativeContractError("selection_diagnostic policy fields differ from its dimension")
    else:
        raise NarrativeContractError("selection_diagnostic code has no supported field shape")
    return item


def _selection_diagnostics(value: object, *, name: str,
                           legacy_aggregate: bool = False) -> tuple[Mapping[str, Any], ...]:
    diagnostics = _array(value, name)
    if len(diagnostics) > 128:
        raise NarrativeContractError(f"{name} array bound exceeded")
    checked = []
    for row in diagnostics:
        if legacy_aggregate and isinstance(row, Mapping) and set(row) == {"code", "count"}:
            code = _text(row["code"], name + ".code")
            if not _TRACE_CODE.fullmatch(code):
                raise NarrativeContractError(f"{name} legacy code is invalid")
            _integer(row["count"], name + ".count", positive=True)
            checked.append(cast(Mapping[str, Any], _freeze_json(dict(row))))
        else:
            checked.append(cast(Mapping[str, Any], _freeze_json(_selection_diagnostic(row))))
    return tuple(checked)


def _trace_counted_samples(value: object, name: str, *, limit: int = 32) -> tuple[int, bool, Sequence[Any]]:
    item = _exact(value, {"count", "limited", "samples"}, name)
    count = _integer(item["count"], name + ".count")
    samples = _array(item["samples"], name + ".samples")
    if len(samples) > limit or type(item["limited"]) is not bool:
        raise NarrativeContractError(f"{name} sample bound or flag is invalid")
    if count < len(samples) or item["limited"] != (count > len(samples)):
        raise NarrativeContractError(f"{name} sample count is inconsistent")
    return count, item["limited"], samples


def _trace_unit_ids(value: object, name: str, *, cap: int = 16) -> tuple[Sequence[str], int, bool]:
    item = _exact(value, {"ids", "count", "limited"}, name)
    ids = _reading_texts(item["ids"], name + ".ids", limit=cap)
    if any(not _NARRATIVE_UNIT_ID.fullmatch(unit_id) for unit_id in ids):
        raise NarrativeContractError(f"{name} contains an invalid unit ID")
    count = _integer(item["count"], name + ".count")
    if count < len(ids) or type(item["limited"]) is not bool or item["limited"] != (count > len(ids)):
        raise NarrativeContractError(f"{name} count is inconsistent")
    return ids, count, item["limited"]


def _trace_package_ref(value: object, name: str) -> str:
    package_ref = _text(value, name)
    if not _READING_PACKAGE_ID.fullmatch(package_ref):
        raise NarrativeContractError(f"{name} is invalid")
    return package_ref


def _selection_trace(value: object, spans: Sequence[EvidenceSpan]) -> Mapping[str, Any]:
    item = _exact(value, {
        "schema_version", "source_unit_count", "admission", "eligible_packages",
        "withheld", "selected",
    }, "selection_trace")
    if item["schema_version"] != "selection-trace/1":
        raise NarrativeContractError("unsupported selection_trace schema")
    source_unit_count = _integer(item["source_unit_count"], "selection_trace.source_unit_count")
    span_ids = {span.span_id for span in spans}

    admission = _exact(item["admission"], {
        "count", "admitted_count", "rejected_count", "limited", "rejection_counts", "samples",
    }, "selection_trace.admission")
    count, _, samples = _trace_counted_samples({
        "count": admission["count"], "limited": admission["limited"], "samples": admission["samples"],
    }, "selection_trace.admission")
    admitted = _integer(admission["admitted_count"], "selection_trace.admission.admitted_count")
    rejected = _integer(admission["rejected_count"], "selection_trace.admission.rejected_count")
    if admitted + rejected != count:
        raise NarrativeContractError("selection_trace admission counts are inconsistent")
    rejection_counts = _object(admission["rejection_counts"], "selection_trace.admission.rejection_counts")
    if len(rejection_counts) > 32 or sum(
        _integer(number, "selection_trace.rejection_count", positive=True)
        for number in rejection_counts.values()
    ) != rejected:
        raise NarrativeContractError("selection_trace rejection counts are inconsistent")
    if any(not _TRACE_CODE.fullmatch(code) for code in rejection_counts):
        raise NarrativeContractError("selection_trace rejection code is invalid")
    sampled_admitted = 0
    sampled_rejected = 0
    for raw in samples:
        row = _exact(raw, {
            "unit_id", "package_ref", "status", "reason", "fact_purpose", "fact_reasons",
            "fact_reason_count", "fact_reasons_limited", "required_unit_ids", "required_unit_count",
            "required_unit_ids_limited", "priority", "selected_span_id",
        }, "selection_trace.admission.sample")
        unit_id = _text(row["unit_id"], "selection_trace.admission.unit_id")
        if not _NARRATIVE_UNIT_ID.fullmatch(unit_id):
            raise NarrativeContractError("selection_trace unit ID is invalid")
        _trace_package_ref(row["package_ref"], "selection_trace.admission.package_ref")
        if row["status"] not in {"admitted", "not_admitted"}:
            raise NarrativeContractError("selection_trace admission status is invalid")
        if row["status"] == "admitted":
            sampled_admitted += 1
        else:
            sampled_rejected += 1
        reason = row["reason"]
        if row["status"] == "admitted" and reason is not None:
            raise NarrativeContractError("admitted selection_trace row cannot have a rejection reason")
        if row["status"] == "not_admitted" and (not isinstance(reason, str) or not _TRACE_CODE.fullmatch(reason)):
            raise NarrativeContractError("rejected selection_trace row requires a reason code")
        purpose = _text(row["fact_purpose"], "selection_trace.fact_purpose")
        if not _TRACE_CODE.fullmatch(purpose):
            raise NarrativeContractError("selection_trace fact purpose is invalid")
        fact_reasons = _reading_texts(row["fact_reasons"], "selection_trace.fact_reasons", limit=4)
        fact_reason_count = _integer(row["fact_reason_count"], "selection_trace.fact_reason_count")
        if (fact_reason_count < len(fact_reasons) or type(row["fact_reasons_limited"]) is not bool
                or row["fact_reasons_limited"] != (fact_reason_count > len(fact_reasons))):
            raise NarrativeContractError("selection_trace fact reason sample is inconsistent")
        if any(not _TRACE_CODE.fullmatch(code) for code in fact_reasons):
            raise NarrativeContractError("selection_trace fact reason code is invalid")
        required = _reading_texts(row["required_unit_ids"], "selection_trace.required_unit_ids", limit=8)
        required_count = _integer(row["required_unit_count"], "selection_trace.required_unit_count")
        if (required_count < len(required) or type(row["required_unit_ids_limited"]) is not bool
                or row["required_unit_ids_limited"] != (required_count > len(required))
                or any(not _NARRATIVE_UNIT_ID.fullmatch(unit_id) for unit_id in required)):
            raise NarrativeContractError("selection_trace required unit sample is inconsistent")
        _integer(row["priority"], "selection_trace.priority", positive=True)
        selected_span = row["selected_span_id"]
        if selected_span is not None and (not _EVIDENCE_SPAN_ID.fullmatch(_text(selected_span, "selection_trace.selected_span_id"))
                                          or selected_span not in span_ids):
            raise NarrativeContractError("selection_trace selected span is not in the public evidence")
    if sampled_admitted > admitted or sampled_rejected > rejected:
        raise NarrativeContractError("selection_trace admission sample exceeds aggregate status count")

    packages_count, _, package_samples = _trace_counted_samples(
        item["eligible_packages"], "selection_trace.eligible_packages", limit=16,
    )
    for raw in package_samples:
        row = _exact(raw, {
            "package_ref", "kind", "member_unit_ids", "member_count", "member_limited",
            "anchor_unit_ids", "anchor_count", "anchor_limited", "required_unit_ids",
            "required_count", "required_limited",
        }, "selection_trace.eligible_package")
        _trace_package_ref(row["package_ref"], "selection_trace.eligible_package.package_ref")
        if not _TRACE_CODE.fullmatch(_text(row["kind"], "selection_trace.eligible_package.kind")):
            raise NarrativeContractError("selection_trace package kind is invalid")
        for ids_key, count_key, limited_key in (
            ("member_unit_ids", "member_count", "member_limited"),
            ("anchor_unit_ids", "anchor_count", "anchor_limited"),
            ("required_unit_ids", "required_count", "required_limited"),
        ):
            ids = _reading_texts(row[ids_key], "selection_trace.eligible_package." + ids_key, limit=8)
            count_value = _integer(row[count_key], "selection_trace.eligible_package." + count_key)
            if (any(not _NARRATIVE_UNIT_ID.fullmatch(unit_id) for unit_id in ids)
                    or count_value < len(ids) or type(row[limited_key]) is not bool
                    or row[limited_key] != (count_value > len(ids))):
                raise NarrativeContractError("selection_trace eligible package IDs are inconsistent")

    withheld_count, _, withheld_samples = _trace_counted_samples(
        item["withheld"], "selection_trace.withheld",
    )
    for raw in withheld_samples:
        row = _exact(raw, {
            "package_ref", "reason", "status", "known_unit_ids", "known_unit_count", "known_unit_ids_limited",
        }, "selection_trace.withheld.sample")
        _trace_package_ref(row["package_ref"], "selection_trace.withheld.package_ref")
        if not _TRACE_CODE.fullmatch(_text(row["reason"], "selection_trace.withheld.reason")):
            raise NarrativeContractError("selection_trace withheld reason is invalid")
        if row["status"] is not None and not _TRACE_CODE.fullmatch(_text(row["status"], "selection_trace.withheld.status")):
            raise NarrativeContractError("selection_trace withheld status is invalid")
        _trace_unit_ids({
            "ids": row["known_unit_ids"], "count": row["known_unit_count"],
            "limited": row["known_unit_ids_limited"],
        }, "selection_trace.withheld.known_unit_ids", cap=8)

    selected_count, _, selected_samples = _trace_counted_samples(
        item["selected"], "selection_trace.selected",
    )
    if (not len(spans) <= selected_count <= source_unit_count
            or (not spans and selected_count != 0)):
        raise NarrativeContractError("selection_trace selected count is inconsistent with source evidence")
    unique_units: set[str] = set()
    for raw in selected_samples:
        row = _exact(raw, {"unit_id", "span_id"}, "selection_trace.selected.sample")
        unit_id = _text(row["unit_id"], "selection_trace.selected.unit_id")
        span_id = _text(row["span_id"], "selection_trace.selected.span_id")
        if not _NARRATIVE_UNIT_ID.fullmatch(unit_id) or not _EVIDENCE_SPAN_ID.fullmatch(span_id):
            raise NarrativeContractError("selection_trace selected ID is invalid")
        if unit_id in unique_units or span_id not in span_ids:
            raise NarrativeContractError("selection_trace selected mapping is inconsistent")
        unique_units.add(unit_id)
    if selected_count < len(unique_units) or packages_count < len(package_samples) or withheld_count < len(withheld_samples):
        raise NarrativeContractError("selection_trace sample counts are inconsistent")
    return cast(Mapping[str, Any], _freeze_json(item))


def _reading_context(
    value: object, spans: Sequence[EvidenceSpan],
) -> Mapping[str, Any] | None:
    if value is None:
        return None
    from company_wiki.document_understanding.reading_context_contract import (
        ATTRIBUTED_READING_CONTEXT_SCHEMAS, READING_CONTEXT_SCHEMAS,
        TRACED_READING_CONTEXT_SCHEMAS, SUMMARY_USE_CONTEXT_SCHEMAS,
        validate_summary_support_use,
    )
    plain = _bounded_reading_json(value)
    extra: set[str] = set()
    if isinstance(plain, Mapping) and "deferred_count" in plain:
        extra |= {"deferred_count", "deferred_limited", "selection_diagnostics"}
    if isinstance(plain, Mapping) and plain.get("schema_version") in TRACED_READING_CONTEXT_SCHEMAS:
        extra |= {"deferred_count", "deferred_limited", "selection_diagnostics", "selection_trace"}
    item = _exact(plain, {
        "schema_version", "reading_policy_version", "reading_policies", "business_facets",
        "constraints", "groups", "unread", "deferred", "layout_coverage",
    } | extra, "reading_context")
    if item["schema_version"] not in READING_CONTEXT_SCHEMAS:
        raise NarrativeContractError("unsupported reading_context schema")
    attributed = item["schema_version"] in ATTRIBUTED_READING_CONTEXT_SCHEMAS
    assessed = item['schema_version'] in SUMMARY_USE_CONTEXT_SCHEMAS
    version = _text(item["reading_policy_version"], "reading_policy_version")
    prefix = "du-sent-policy/1+"
    if not version.startswith(prefix):
        raise NarrativeContractError("invalid reading_policy_version")
    _sha(version.removeprefix(prefix), "reading_policy_version digest")
    policies = _array(item["reading_policies"], "reading_policies")
    facets = _array(item["business_facets"], "business_facets")
    if len(policies) > 128 or len(facets) > 16:
        raise NarrativeContractError("reading_context policy bound exceeded")
    for row in policies:
        policy = _exact(row, _READING_POLICY_KEYS, "reading_policy")
        for component in _array(policy["policy_components"] or [], "policy_components"):
            component = _exact(component, {"kind", "id", "version", "content_digest"}, "policy_component")
            _sha(component["content_digest"], "policy_component.content_digest")
    for row in facets:
        facet = _exact(row, _READING_FACET_KEYS, "business_facet")
        _sha(facet["content_digest"], "business_facet.content_digest")
        for check in _array(facet["confusion_checks"] or [], "confusion_checks"):
            check = _exact(check, {"risk", "required_context_slots"}, "confusion_check")
            _text(check["risk"], "confusion_check.risk")
            _reading_texts(check["required_context_slots"], "required_context_slots")
    _reading_texts(item["constraints"], "reading_context.constraints", limit=32)
    sources = {span.span_id: span.source_id for span in spans}
    group_ids: set[str] = set()
    groups = _array(item["groups"], "reading_context.groups")
    if len(groups) > 512:
        raise NarrativeContractError("reading_context group bound exceeded")
    for row in groups:
        proof_fields = {"source_proof_unit_ids", "source_proof_target_unit_ids", "source_proofs"}
        supplied_proof_fields = set(row) & proof_fields if isinstance(row, Mapping) else set()
        if supplied_proof_fields and (not attributed or supplied_proof_fields != proof_fields):
            raise NarrativeContractError("reading_group native source proof fields must be paired and attributed")
        group = _exact(row, {"group_id", "kind", "section_role", "evidence_ids"}
                       | ({"citation_views"} if attributed else set()) | supplied_proof_fields,
                       "reading_group")
        group_id = _text(group["group_id"], "reading_group.group_id")
        if group_id in group_ids:
            raise NarrativeContractError("duplicate reading_context group ids")
        group_ids.add(group_id)
        _text(group["kind"], "reading_group.kind")
        _text(group["section_role"], "reading_group.section_role")
        refs = _reading_texts(group["evidence_ids"], "reading_group.evidence_ids")
        if not refs or len(refs) != len(set(refs)) or any(ref not in sources for ref in refs):
            raise NarrativeContractError("reading_group requires unique selected evidence references")
        if len({sources[ref] for ref in refs}) != 1:
            raise NarrativeContractError("reading_group cannot cross original source parents")
        if attributed:
            views = _array(group["citation_views"], "reading_group.citation_views")
            if not 1 <= len(views) <= 2:
                raise NarrativeContractError("reading_group requires one or two citation views")
            seen_support: set[frozenset[str]] = set()
            for value in views:
                view = _exact(value, {"support_evidence_ids", "context_evidence_ids"}
                    | ({'reading_support_use', 'reading_support_reason'} if assessed else set()), "citation_view")
                if assessed:
                    try:
                        validate_summary_support_use(view['reading_support_use'], view['reading_support_reason'])
                    except ValueError as exc:
                        raise NarrativeContractError(str(exc)) from exc
                support = _reading_texts(view["support_evidence_ids"], "citation_view.support_evidence_ids")
                context = _reading_texts(view["context_evidence_ids"], "citation_view.context_evidence_ids")
                if (not support or len(support) != len(set(support)) or len(context) != len(set(context))
                        or set(support) & set(context) or set(support) | set(context) != set(refs)):
                    raise NarrativeContractError("citation_view must partition its complete original group")
                identity = frozenset(support)
                if identity in seen_support:
                    raise NarrativeContractError("duplicate reading_group citation views")
                seen_support.add(identity)
        if supplied_proof_fields:
            proof_ids = _reading_texts(
                group["source_proof_unit_ids"], "reading_group.source_proof_unit_ids", limit=128,
            )
            target_ids = _reading_texts(
                group["source_proof_target_unit_ids"],
                "reading_group.source_proof_target_unit_ids", limit=256,
            )
            if (not proof_ids or len(proof_ids) != len(set(proof_ids))
                    or len(target_ids) != len(set(target_ids))
                    or any(not _NARRATIVE_UNIT_ID.fullmatch(unit_id)
                           for unit_id in (*proof_ids, *target_ids))):
                raise NarrativeContractError("reading_group native source proof IDs are invalid")
            # The producer excludes a dependency's target from its physical
            # refs, so validate closure over both explicitly separated sets.
            proof_id_set = set(proof_ids) | set(target_ids)
            proof_rows = _array(group["source_proofs"], "reading_group.source_proofs")
            if not proof_rows or len(proof_rows) > 128:
                raise NarrativeContractError("reading_group native source proofs are outside their bound")
            seen_edges: set[tuple[str, str]] = set()
            for raw_proof in proof_rows:
                proof = _exact(raw_proof, {
                    "basis", "left", "right", "left_page", "right_page", "left_ordinal",
                    "right_ordinal", "column", "coordinate_frame", "furniture_unit_ids",
                }, "reading_group.source_proof")
                if _text(proof["basis"], "source_proof.basis") != "observed_adjacent_page_flow":
                    raise NarrativeContractError("reading_group source proof basis is unsupported")
                left = _text(proof["left"], "source_proof.left")
                right = _text(proof["right"], "source_proof.right")
                if (not _NARRATIVE_UNIT_ID.fullmatch(left) or not _NARRATIVE_UNIT_ID.fullmatch(right)
                        or left == right or not {left, right} <= proof_id_set):
                    raise NarrativeContractError("reading_group source proof endpoints are invalid")
                edge = (left, right)
                if edge in seen_edges:
                    raise NarrativeContractError("duplicate reading_group source proof edge")
                seen_edges.add(edge)
                left_page = _integer(proof["left_page"], "source_proof.left_page", positive=True)
                right_page = _integer(proof["right_page"], "source_proof.right_page", positive=True)
                if right_page != left_page + 1:
                    raise NarrativeContractError("reading_group source proof pages are not adjacent")
                left_ordinal = _integer(proof["left_ordinal"], "source_proof.left_ordinal")
                right_ordinal = _integer(proof["right_ordinal"], "source_proof.right_ordinal")
                if right_ordinal <= left_ordinal:
                    raise NarrativeContractError("reading_group source proof ordinals are not ordered")
                column = proof["column"]
                if type(column) is not int and not isinstance(column, str):
                    raise NarrativeContractError("reading_group source proof column is invalid")
                if isinstance(column, str):
                    _text(column, "source_proof.column")
                    if len(column) > 256:
                        raise NarrativeContractError("reading_group source proof column is too long")
                frame = _text(proof["coordinate_frame"], "source_proof.coordinate_frame")
                if len(frame) > 256:
                    raise NarrativeContractError("reading_group source proof coordinate frame is too long")
                furniture = _reading_texts(
                    proof["furniture_unit_ids"], "source_proof.furniture_unit_ids", limit=24,
                )
                if (len(furniture) != len(set(furniture))
                        or any(not _NARRATIVE_UNIT_ID.fullmatch(unit_id) for unit_id in furniture)
                        or not set(furniture) <= proof_id_set):
                    raise NarrativeContractError("reading_group source proof furniture IDs are invalid")
    unread_keys = {
        "native_scan", "opaque_pages", "deferred_pages", "deferred_unit_ids",
        "unassigned_unit_ids", "structure_complete",
    }
    sampled = isinstance(item["unread"], Mapping) and bool({"counts", "limited"} & set(item["unread"]))
    unread = _exact(item["unread"], unread_keys | ({"counts", "limited"} if sampled else set()), "reading_context.unread")
    _text(unread["native_scan"], "unread.native_scan", optional=True)
    if unread["structure_complete"] is not None and type(unread["structure_complete"]) is not bool:
        raise NarrativeContractError("unread.structure_complete must be boolean or null")
    for name in ("opaque_pages", "deferred_pages"):
        for number in _array(unread[name], "unread." + name):
            _integer(number, "unread page", positive=True)
    for name in ("deferred_unit_ids", "unassigned_unit_ids"):
        _reading_texts(unread[name], "unread." + name)
    if sampled:
        array_names = {"opaque_pages", "deferred_pages", "deferred_unit_ids", "unassigned_unit_ids"}
        counts = _exact(unread["counts"], array_names, "unread.counts")
        for name, number in counts.items():
            if _integer(number, "unread.count") < len(unread[name]):
                raise NarrativeContractError("unread count cannot be smaller than its diagnostic sample")
        if type(unread["limited"]) is not bool or unread["limited"] != any(
            counts[name] > len(unread[name]) for name in array_names
        ):
            raise NarrativeContractError("unread.limited differs from its complete counts")
    for row in _array(item["deferred"], "reading_context.deferred"):
        deferred = _exact(row, {"package_id", "reason"}, "reading_deferred")
        _text(deferred["package_id"], "reading_deferred.package_id")
        _text(deferred["reason"], "reading_deferred.reason")
    _object(item["layout_coverage"], "reading_context.layout_coverage")
    if extra:
        count = _integer(item["deferred_count"], "deferred_count")
        rows = item["deferred"]
        if count < len(rows) or type(item["deferred_limited"]) is not bool or item["deferred_limited"] != (count > len(rows)):
            raise NarrativeContractError("deferred sampling differs from its complete count")
        _selection_diagnostics(
            item["selection_diagnostics"], name="selection_diagnostics",
            legacy_aggregate=item["schema_version"] == "du-production-reading/2",
        )
        if "selection_trace" in extra:
            _selection_trace(item["selection_trace"], spans)
    _enforce_cap(item, READING_CONTEXT_MAX_BYTES, "reading_context")
    return cast(Mapping[str, Any], _freeze_json(plain))


def _reading_dependencies(value: object) -> Mapping[str, Any] | None:
    if value is None:
        return None
    item = _exact(_bounded_reading_json(value), {
        "schema_version", "status", "scopes", "components", "candidates", "versions",
        "decision_digest", "diagnostics",
    }, "reading_dependencies")
    if item["schema_version"] != "du-decision-dependencies/1" or item["status"] not in {"complete", "partial"}:
        raise NarrativeContractError("invalid reading dependency schema/status")
    _sha(item["decision_digest"], "decision_digest", optional=item["status"] == "partial")
    for key, bound in (("scopes", 64), ("components", 512), ("candidates", 4096)):
        if len(_array(item[key], "reading_dependencies." + key)) > bound:
            raise NarrativeContractError("reading dependency inventory exceeds its bound")
    _object(item["versions"], "reading dependency versions")
    assert_no_physical_paths(item)
    _enforce_cap(item, READING_CONTEXT_MAX_BYTES, "reading_dependencies")
    return cast(Mapping[str, Any], _freeze_json(item))


@dataclass(frozen=True)
class NarrativeSelectResult:
    schema_version: str
    source_ref: SourceRefValue
    expected_read_policy_sha256: str | None
    source_metadata: SourceMetadataValue
    parser: ComponentValue
    selector: ComponentValue
    selection: SelectionValue
    evidence_spans: tuple[EvidenceSpan, ...]
    prompt_review: PromptReviewValue
    transcript_lineage: TranscriptLineageValue | None
    transcript_byte_bindings: tuple[TranscriptByteBinding, ...]
    summary_scope: str
    encoded_size: int
    subject_binding: NarrativeSubject | None = None
    reading_context: Mapping[str, Any] | None = None
    reading_dependencies: Mapping[str, Any] | None = None
    selection_diagnostics: tuple[Mapping[str, Any], ...] = ()

    @classmethod
    def from_dict(cls, value: object) -> "NarrativeSelectResult":
        _assert_pathless_reading_wire(value)
        keys = {
            "schema_version",
            "source_ref",
            "expected_read_policy_sha256",
            "source_metadata",
            "parser",
            "selector",
            "selection",
            "evidence_spans",
            "prompt_review",
            "transcript_lineage",
            "transcript_byte_bindings",
            "summary_scope",
        }
        projected = (
            isinstance(value, Mapping)
            and value.get("schema_version") in PROJECTED_SELECT_RESULT_SCHEMAS
        )
        if projected:
            keys = (
                keys
                - {
                    "source_ref",
                    "expected_read_policy_sha256",
                    "transcript_lineage",
                    "transcript_byte_bindings",
                }
            ) | {"subject_binding"}
        if isinstance(value, Mapping) and "reading_context" in value:
            keys.add("reading_context")
        if isinstance(value, Mapping) and "reading_dependencies" in value:
            keys.add("reading_dependencies")
        if isinstance(value, Mapping) and "selection_diagnostics" in value:
            keys.add("selection_diagnostics")
        if (isinstance(value, Mapping) and "reading_context" in value
                and "selection_diagnostics" in value):
            raise NarrativeContractError(
                "selection diagnostics cannot be split between top-level and reading_context"
            )
        item = _exact(value, keys, "narrative select result")
        if item["schema_version"] not in SUPPORTED_SELECT_RESULT_SCHEMAS:
            raise NarrativeContractError("unsupported narrative select schema")
        subject = _projection_subject(item["subject_binding"]) if projected else None
        source = SourceRefValue.from_dict(
            subject.anchor_ref if subject is not None else item["source_ref"]
        )
        metadata = SourceMetadataValue.from_dict(
            item["source_metadata"], projected=projected
        )
        selection = SelectionValue.from_dict(item["selection"])
        spans = _evidence(item["evidence_spans"])
        review = PromptReviewValue.from_dict(item["prompt_review"])
        review.validate_source(source)
        lineage = (
            None
            if projected or item["transcript_lineage"] is None
            else TranscriptLineageValue.from_dict(item["transcript_lineage"])
        )
        bindings = tuple(
            TranscriptByteBinding.from_dict(raw)
            for raw in _array(
                item.get("transcript_byte_bindings", []), "transcript_byte_bindings"
            )
        )
        result = cls(
            item["schema_version"],
            source,
            None
            if projected
            else _sha(
                item["expected_read_policy_sha256"], "expected_read_policy_sha256"
            ),
            metadata,
            ComponentValue.from_dict(item["parser"], "parser"),
            ComponentValue.from_dict(item["selector"], "selector"),
            selection,
            spans,
            review,
            lineage,
            bindings,
            _text(item["summary_scope"], "summary_scope"),
            0,
            subject,
            _reading_context(item.get("reading_context"), spans),
            _reading_dependencies(item.get("reading_dependencies")),
            _selection_diagnostics(item.get("selection_diagnostics", []), name="selection_diagnostics"),
        )
        result._validate()
        size = _enforce_cap(result.to_dict(), SELECT_RESULT_MAX_BYTES, "select")
        object.__setattr__(result, "encoded_size", size)
        return result

    def _validate(self) -> None:
        if self.summary_scope != "selected_evidence_only":
            raise NarrativeContractError("summary_scope must be selected_evidence_only")
        if self.selection.selected_count != len(self.evidence_spans):
            raise NarrativeContractError(
                "selection selected_count differs from evidence"
            )
        if self.subject_binding is not None:
            _validate_projection_evidence(
                self.subject_binding, self.evidence_spans, self.selection
            )
        elif any(
            span.source_id != self.source_ref.source_id for span in self.evidence_spans
        ):
            raise NarrativeContractError(
                "selected evidence source differs from source_ref"
            )
        if self.selection.status == "skipped_no_narrative":
            if self.evidence_spans or not self.selection.coverage_complete:
                raise NarrativeContractError(
                    "skip requires complete coverage and no evidence"
                )
        self._validate_transcript_fields()

    def _validate_transcript_fields(self) -> None:
        if self.source_metadata.source_class in {"filing", "official_json"}:
            if self.transcript_lineage or self.transcript_byte_bindings:
                raise NarrativeContractError(
                    "filing result cannot contain transcript fields"
                )
            return
        if self.transcript_lineage is None:
            raise NarrativeContractError("transcript result requires source lineage")
        lineage = self.transcript_lineage.values
        if (
            lineage["original_source_id"] != self.source_ref.source_id
            or lineage["original_sha256"] != self.source_ref.content_sha256
        ):
            raise NarrativeContractError("transcript lineage differs from source_ref")
        bound = {binding.evidence_id for binding in self.transcript_byte_bindings}
        selected = {span.span_id for span in self.evidence_spans}
        if bound != selected:
            raise NarrativeContractError(
                "transcript bindings must match selected evidence"
            )

    @property
    def subject(self) -> NarrativeSubject:
        return self.subject_binding or NarrativeSubject.from_raw(
            self.source_ref.to_dict()
        )

    @property
    def item_key(self) -> str:
        return (
            self.subject_binding.item_key
            if self.subject_binding is not None
            else self.source_ref.document_id
        )

    def to_dict(self) -> dict[str, Any]:
        value = {
            "schema_version": self.schema_version,
            "source_ref": self.source_ref.to_dict(),
            "expected_read_policy_sha256": self.expected_read_policy_sha256,
            "source_metadata": self.source_metadata.to_dict(),
            "parser": self.parser.to_dict(),
            "selector": self.selector.to_dict(),
            "selection": self.selection.to_dict(),
            "evidence_spans": [span.to_dict() for span in self.evidence_spans],
            "prompt_review": self.prompt_review.to_dict(),
            "transcript_lineage": self.transcript_lineage.to_dict()
            if self.transcript_lineage
            else None,
            "transcript_byte_bindings": [
                item.to_dict() for item in self.transcript_byte_bindings
            ],
            "summary_scope": self.summary_scope,
        }
        if self.reading_context is not None:
            value["reading_context"] = _to_plain(self.reading_context)
        if self.reading_dependencies is not None:
            value["reading_dependencies"] = _to_plain(self.reading_dependencies)
        if self.selection_diagnostics:
            value["selection_diagnostics"] = _to_plain(self.selection_diagnostics)
        return _subject_wire(
            value,
            self.subject_binding,
            remove=(
                "source_ref",
                "expected_read_policy_sha256",
                "transcript_lineage",
                "transcript_byte_bindings",
            ),
        )


def _claim_from_dict(value: object) -> SummaryClaim:
    item = _exact(
        value,
        {"claim_id", "text", "evidence_ids", "claim_type", "modality", "needs_review"}
        | ({"context_evidence_ids"} if isinstance(value, Mapping) and "context_evidence_ids" in value else set()),
        "summary claim",
    )
    evidence_ids = tuple(
        _text(raw, "summary claim evidence_id")
        for raw in _array(item["evidence_ids"], "summary claim evidence_ids")
    )
    if type(item["needs_review"]) is not bool:
        raise NarrativeContractError("summary claim needs_review must be boolean")
    claim_type = _text(item["claim_type"], "summary claim claim type")
    if claim_type not in {
        "company_statement",
        "analyst_question",
        "editorial",
        "uncertain",
    }:
        raise NarrativeContractError("summary claim type is invalid")
    modality = _text(item["modality"], "summary claim modality")
    if modality not in {
        "actual",
        "planned",
        "forecast",
        "question",
        "negation",
        "uncertain",
    }:
        raise NarrativeContractError("summary claim modality is invalid")
    return SummaryClaim(
        claim_id=_text(item["claim_id"], "summary claim claim_id"),
        text=_text(item["text"], "summary claim text"),
        evidence_ids=evidence_ids,
        claim_type=cast(
            Literal["company_statement", "analyst_question", "editorial", "uncertain"],
            claim_type,
        ),
        modality=cast(
            Literal[
                "actual",
                "planned",
                "forecast",
                "question",
                "negation",
                "uncertain",
            ],
            modality,
        ),
        needs_review=item["needs_review"],
        context_evidence_ids=tuple(_text(raw, "summary claim context evidence_id")
            for raw in _array(item.get("context_evidence_ids", ()), "summary claim context_evidence_ids")),
    )


def _draft_from_dict(value: object) -> SourceSummaryDraft:
    item = _exact(
        value,
        {"source_id", "source_sha256", "language", "claims", "status"},
        "summary draft",
    )
    claims = tuple(
        _claim_from_dict(raw) for raw in _array(item["claims"], "summary claims")
    )
    status = _text(item["status"], "summary draft status")
    if status not in {"draft", "needs_review"}:
        raise NarrativeContractError("summary draft status is invalid")
    return SourceSummaryDraft(
        source_id=_text(item["source_id"], "summary draft source_id"),
        source_sha256=_sha(item["source_sha256"], "summary draft source_sha256"),
        language=_text(item["language"], "summary draft language"),
        claims=claims,
        status=cast(Literal["draft", "needs_review"], status),
    )


def _claim_to_dict(claim: SummaryClaim) -> dict[str, Any]:
    result: dict[str, Any] = {"claim_id": claim.claim_id, "text": claim.text,
        "evidence_ids": list(claim.evidence_ids), "claim_type": claim.claim_type,
        "modality": claim.modality, "needs_review": claim.needs_review}
    if claim.context_evidence_ids:
        result["context_evidence_ids"] = list(claim.context_evidence_ids)
    return result


def _draft_to_dict(value: SourceSummaryDraft) -> dict[str, Any]:
    return {
        "source_id": value.source_id,
        "source_sha256": value.source_sha256,
        "language": value.language,
        "claims": [_claim_to_dict(claim) for claim in value.claims],
        "status": value.status,
    }


@dataclass(frozen=True)
class SubjectSummaryDraft:
    subject_id: str
    subject_sha256: str
    language: str
    claims: tuple[SummaryClaim, ...]
    status: Literal["draft", "needs_review"] = "draft"


def subject_draft_from_dict(value: object) -> SubjectSummaryDraft:
    item = _exact(
        value,
        {"subject_id", "subject_sha256", "language", "claims", "status"},
        "subject summary draft",
    )
    status = _text(item["status"], "subject summary status")
    if status not in {"draft", "needs_review"}:
        raise NarrativeContractError("subject summary status is invalid")
    return SubjectSummaryDraft(
        _text(item["subject_id"], "subject summary ID"),
        _sha(item["subject_sha256"], "subject summary SHA"),
        _text(item["language"], "subject summary language"),
        tuple(
            _claim_from_dict(raw) for raw in _array(item["claims"], "summary claims")
        ),
        cast(Literal["draft", "needs_review"], status),
    )


def subject_draft_to_dict(value: SubjectSummaryDraft) -> dict[str, Any]:
    return {
        "subject_id": value.subject_id,
        "subject_sha256": value.subject_sha256,
        "language": value.language,
        "status": value.status,
        "claims": [_claim_to_dict(claim) for claim in value.claims],
    }


def validate_subject_summary_identity(
    draft: SubjectSummaryDraft, *, subject: NarrativeSubject, language: str
) -> None:
    if (
        draft.subject_id != subject.item_key
        or draft.subject_sha256 != subject.subject_sha256
    ):
        raise SummaryValidationError("summary subject identity/hash does not match")
    if draft.language != language:
        raise SummaryValidationError(
            "summary language must match the selected language"
        )


def validate_subject_summary_draft(
    draft: SubjectSummaryDraft,
    *,
    subject: NarrativeSubject,
    language: str,
    evidence_spans: Sequence[EvidenceSpan],
) -> None:
    validate_subject_summary_identity(draft, subject=subject, language=language)
    if not draft.claims:
        raise SummaryValidationError("summary draft must contain at least one claim")
    known = {span.span_id: span for span in evidence_spans}
    for claim in draft.claims:
        validate_summary_claim(claim, known, draft.status)


def _summary_draft_dict(
    value: SourceSummaryDraft | SubjectSummaryDraft,
) -> dict[str, Any]:
    return (
        subject_draft_to_dict(value)
        if isinstance(value, SubjectSummaryDraft)
        else _draft_to_dict(value)
    )


@dataclass(frozen=True)
class ModelValue:
    adapter_id: str
    model_id: str
    prompt_version: str
    response_sha256: str

    @classmethod
    def from_dict(cls, value: object) -> "ModelValue":
        item = _exact(
            value,
            {"adapter_id", "model_id", "prompt_version", "response_sha256"},
            "model",
        )
        return cls(
            _text(item["adapter_id"], "model.adapter_id"),
            _text(item["model_id"], "model.model_id"),
            _text(item["prompt_version"], "model.prompt_version"),
            _sha(item["response_sha256"], "model.response_sha256"),
        )

    def to_dict(self) -> dict[str, str]:
        return {
            "adapter_id": self.adapter_id,
            "model_id": self.model_id,
            "prompt_version": self.prompt_version,
            "response_sha256": self.response_sha256,
        }


@dataclass(frozen=True)
class NarrativeSummaryResult:
    schema_version: str
    source_ref: SourceRefValue
    language: str
    translate: bool
    status: str
    draft: SourceSummaryDraft | SubjectSummaryDraft | None
    model: ModelValue | None
    prompt_review: PromptReviewValue
    encoded_size: int
    subject_binding: NarrativeSubject | None = None

    @classmethod
    def from_dict(cls, value: object) -> "NarrativeSummaryResult":
        assert_no_physical_paths(value)
        projected = (
            isinstance(value, Mapping)
            and value.get("schema_version") == PROJECTED_SUMMARY_RESULT_SCHEMA
        )
        keys = {
            "schema_version",
            "source_ref",
            "language",
            "translate",
            "status",
            "draft",
            "model",
            "prompt_review",
        }
        if projected:
            keys = (keys - {"source_ref"}) | {"subject_binding"}
        item = _exact(value, keys, "narrative summary result")
        if item["schema_version"] not in {
            SUMMARY_RESULT_SCHEMA,
            PROJECTED_SUMMARY_RESULT_SCHEMA,
        }:
            raise NarrativeContractError("unsupported narrative summary schema")
        if item["translate"] is not False:
            raise NarrativeContractError("translate must be false")
        subject = _projection_subject(item["subject_binding"]) if projected else None
        source = SourceRefValue.from_dict(
            subject.anchor_ref if subject is not None else item["source_ref"]
        )
        language = _text(item["language"], "summary language")
        status = _text(item["status"], "summary status")
        unknown_skip = (
            projected and language == "unknown" and status == "summary_not_needed"
        )
        if language not in _LANGUAGES and not unknown_skip:
            raise NarrativeContractError("summary language is invalid")
        draft = (
            None
            if item["draft"] is None
            else subject_draft_from_dict(item["draft"])
            if projected
            else _draft_from_dict(item["draft"])
        )
        model = None if item["model"] is None else ModelValue.from_dict(item["model"])
        if status == "completed" and (draft is None or model is None):
            raise NarrativeContractError("completed summary requires draft and model")
        if status == "summary_not_needed" and (draft is not None or model is not None):
            raise NarrativeContractError(
                "summary_not_needed must not contain draft or model"
            )
        if status not in {"completed", "summary_not_needed"}:
            raise NarrativeContractError("summary status is invalid")
        review = PromptReviewValue.from_dict(item["prompt_review"])
        review.validate_source(source)
        result = cls(
            item["schema_version"],
            source,
            language,
            False,
            status,
            draft,
            model,
            review,
            0,
            subject,
        )
        result._validate_identity()
        size = _enforce_cap(result.to_dict(), SUMMARY_RESULT_MAX_BYTES, "summary")
        object.__setattr__(result, "encoded_size", size)
        return result

    def _validate_identity(self) -> None:
        if self.draft is None:
            return
        if self.subject_binding is not None:
            if not isinstance(self.draft, SubjectSummaryDraft):
                raise NarrativeContractError(
                    "projection summary requires subject draft"
                )
            if (
                self.draft.subject_id != self.subject_binding.item_key
                or self.draft.subject_sha256 != self.subject_binding.subject_sha256
            ):
                raise NarrativeContractError(
                    "summary draft subject differs from selection"
                )
        elif not isinstance(self.draft, SourceSummaryDraft) or (
            self.draft.source_id != self.source_ref.source_id
            or self.draft.source_sha256 != self.source_ref.content_sha256
        ):
            raise NarrativeContractError("summary draft source differs from source_ref")
        if self.draft.language != self.language:
            raise NarrativeContractError("summary draft language differs from result")

    def validate_against(self, selected: NarrativeSelectResult) -> None:
        if (
            self.subject != selected.subject
            or self.language != selected.source_metadata.language
        ):
            raise NarrativeContractError(
                "summary source or language differs from selection"
            )
        skipped = selected.selection.status == "skipped_no_narrative"
        if skipped != (self.status == "summary_not_needed"):
            raise NarrativeContractError("summary status differs from selection")
        if self.status == "completed":
            assert self.draft is not None
            try:
                if isinstance(self.draft, SubjectSummaryDraft):
                    validate_subject_summary_draft(
                        self.draft,
                        subject=selected.subject,
                        language=selected.source_metadata.language,
                        evidence_spans=selected.evidence_spans,
                    )
                else:
                    validate_summary_draft(
                        self.draft,
                        source_id=selected.source_ref.source_id,
                        source_sha256=selected.source_ref.content_sha256,
                        language=selected.source_metadata.language,
                        evidence_spans=selected.evidence_spans,
                    )
            except SummaryValidationError as exc:
                raise NarrativeContractError(str(exc)) from exc

    @property
    def subject(self) -> NarrativeSubject:
        return self.subject_binding or NarrativeSubject.from_raw(
            self.source_ref.to_dict()
        )

    @property
    def item_key(self) -> str:
        return (
            self.subject_binding.item_key
            if self.subject_binding is not None
            else self.source_ref.document_id
        )

    def to_dict(self) -> dict[str, Any]:
        value = {
            "schema_version": self.schema_version,
            "source_ref": self.source_ref.to_dict(),
            "language": self.language,
            "translate": self.translate,
            "status": self.status,
            "draft": _summary_draft_dict(self.draft) if self.draft else None,
            "model": self.model.to_dict() if self.model else None,
            "prompt_review": self.prompt_review.to_dict(),
        }
        return _subject_wire(value, self.subject_binding, remove=("source_ref",))


@dataclass(frozen=True)
class BundleSummaryValue:
    status: str
    translate: bool
    draft: SourceSummaryDraft | SubjectSummaryDraft | None
    model: ModelValue | None

    @classmethod
    def from_dict(
        cls, value: object, *, projected: bool = False
    ) -> "BundleSummaryValue":
        item = _exact(
            value, {"status", "translate", "draft", "model"}, "bundle summary"
        )
        if item["translate"] is not False:
            raise NarrativeContractError("bundle summary translate must be false")
        status = _text(item["status"], "bundle summary status")
        draft = (
            None
            if item["draft"] is None
            else subject_draft_from_dict(item["draft"])
            if projected
            else _draft_from_dict(item["draft"])
        )
        model = None if item["model"] is None else ModelValue.from_dict(item["model"])
        if status == "completed" and (draft is None or model is None):
            raise NarrativeContractError(
                "completed bundle summary requires draft and model"
            )
        if status == "summary_not_needed" and (draft is not None or model is not None):
            raise NarrativeContractError(
                "summary_not_needed bundle cannot contain model"
            )
        return cls(status, False, draft, model)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "translate": self.translate,
            "draft": _summary_draft_dict(self.draft) if self.draft else None,
            "model": self.model.to_dict() if self.model else None,
        }


@dataclass(frozen=True)
class VersionsValue:
    parser: str
    selector: str
    material: str | None
    model: str | None
    prompt: str | None
    bundle_producer: str

    @classmethod
    def from_dict(cls, value: object) -> "VersionsValue":
        item = _exact(
            value,
            {"parser", "selector", "material", "model", "prompt", "bundle_producer"},
            "versions",
        )
        return cls(
            _text(item["parser"], "versions.parser"),
            _text(item["selector"], "versions.selector"),
            _text(item["material"], "versions.material", optional=True),
            _text(item["model"], "versions.model", optional=True),
            _text(item["prompt"], "versions.prompt", optional=True),
            _text(item["bundle_producer"], "versions.bundle_producer"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "parser": self.parser,
            "selector": self.selector,
            "material": self.material,
            "model": self.model,
            "prompt": self.prompt,
            "bundle_producer": self.bundle_producer,
        }


@dataclass(frozen=True)
class ReplayValue:
    required: bool
    locator_count: int

    @classmethod
    def from_dict(cls, value: object) -> "ReplayValue":
        item = _exact(value, {"required", "locator_count"}, "replay")
        if item["required"] is not True:
            raise NarrativeContractError("replay.required must be true")
        return cls(True, _integer(item["locator_count"], "replay.locator_count"))

    def to_dict(self) -> dict[str, Any]:
        return {"required": self.required, "locator_count": self.locator_count}


@dataclass(frozen=True)
class NarrativeBundle:
    schema_version: str
    source_ref: SourceRefValue
    expected_read_policy_sha256: str | None
    source_metadata: SourceMetadataValue
    quality_status: str
    selection: SelectionValue
    evidence_spans: tuple[EvidenceSpan, ...]
    summary: BundleSummaryValue
    prompt_review: PromptReviewValue
    transcript_lineage: TranscriptLineageValue | None
    transcript_byte_bindings: tuple[TranscriptByteBinding, ...]
    versions: VersionsValue
    replay: ReplayValue
    encoded_size: int
    subject_binding: NarrativeSubject | None = None
    reading_context: Mapping[str, Any] | None = None
    summary_assessment: Mapping[str,Any] | None = None

    @classmethod
    def from_dict(cls, value: object) -> "NarrativeBundle":
        _assert_pathless_reading_wire(value)
        keys = {
            "schema_version",
            "source_ref",
            "expected_read_policy_sha256",
            "source_metadata",
            "quality_status",
            "selection",
            "evidence_spans",
            "summary",
            "prompt_review",
            "transcript_lineage",
            "transcript_byte_bindings",
            "versions",
            "replay",
        }
        projected = (
            isinstance(value, Mapping)
            and value.get("schema_version") in {PROJECTED_BUNDLE_SCHEMA,ASSESSED_PROJECTED_BUNDLE_SCHEMA}
        )
        assessed = isinstance(value,Mapping) and value.get('schema_version') in {
            ASSESSED_BUNDLE_SCHEMA,ASSESSED_PROJECTED_BUNDLE_SCHEMA}
        if assessed:
            keys.add('summary_assessment')
        if projected:
            keys = (
                keys
                - {
                    "source_ref",
                    "expected_read_policy_sha256",
                    "transcript_lineage",
                    "transcript_byte_bindings",
                }
            ) | {"subject_binding"}
        if isinstance(value, Mapping) and "reading_context" in value:
            keys.add("reading_context")
        item = _exact(value, keys, "narrative bundle")
        if item["schema_version"] not in {BUNDLE_SCHEMA, PROJECTED_BUNDLE_SCHEMA,
                                          ASSESSED_BUNDLE_SCHEMA,ASSESSED_PROJECTED_BUNDLE_SCHEMA}:
            raise NarrativeContractError("unsupported narrative bundle schema")
        quality = _text(item["quality_status"], "quality_status")
        if quality not in _QUALITY_STATUSES:
            raise NarrativeContractError("quality_status is invalid")
        subject = _projection_subject(item["subject_binding"]) if projected else None
        source = SourceRefValue.from_dict(
            subject.anchor_ref if subject is not None else item["source_ref"]
        )
        review = PromptReviewValue.from_dict(item["prompt_review"])
        review.validate_source(source)
        result = cls(
            item["schema_version"],
            source,
            None
            if projected
            else _sha(
                item["expected_read_policy_sha256"], "expected_read_policy_sha256"
            ),
            SourceMetadataValue.from_dict(item["source_metadata"], projected=projected),
            quality,
            SelectionValue.from_dict(item["selection"]),
            _evidence(item["evidence_spans"]),
            BundleSummaryValue.from_dict(item["summary"], projected=projected),
            review,
            None
            if projected or item["transcript_lineage"] is None
            else TranscriptLineageValue.from_dict(item["transcript_lineage"]),
            tuple(
                TranscriptByteBinding.from_dict(raw)
                for raw in _array(
                    item.get("transcript_byte_bindings", []), "transcript_byte_bindings"
                )
            ),
            VersionsValue.from_dict(item["versions"]),
            ReplayValue.from_dict(item["replay"]),
            0,
            subject,
        )
        object.__setattr__(result, "reading_context", _reading_context(item.get("reading_context"), result.evidence_spans))
        if assessed:
            object.__setattr__(result,'summary_assessment',_freeze_json(item['summary_assessment']))
        result._validate()
        cap = (
            SKIP_BUNDLE_MAX_BYTES
            if quality == "skipped_no_narrative"
            else BUNDLE_MAX_BYTES
        )
        size = _enforce_cap(result.to_dict(), cap, "bundle")
        object.__setattr__(result, "encoded_size", size)
        return result

    def _validate(self) -> None:
        from .narrative_summary_protocols import summary_bundle_format, scoped_protocol_for_prompt
        prompt = self.summary.model.prompt_version if self.summary.model else self.versions.prompt
        recipe=summary_bundle_format(prompt)
        protocol = None
        if recipe.assessed:
            assert prompt is not None
            protocol = scoped_protocol_for_prompt(prompt)
        expected_schema=recipe.projected_schema if self.subject_binding is not None else recipe.raw_schema
        if self.schema_version!=expected_schema:
            raise NarrativeContractError('bundle schema differs from its summary protocol')
        if recipe.assessed and self.summary.model is None:
            if (self.summary.status!='summary_not_needed' or self.summary.draft is not None
                    or self.summary_assessment is not None or self.quality_status!='skipped_no_narrative'
                    or self.versions.model is not None or self.versions.bundle_producer!=recipe.producer):
                raise NarrativeContractError('assessed skip bundle contains model or assessment')
        elif recipe.assessed:
            assert protocol is not None
            from .narrative_summary_assessment import validate_assessment_material, validate_assessment_quality
            if (self.versions.bundle_producer!=recipe.producer or self.summary.draft is None
                    or self.summary.model is None):
                raise NarrativeContractError('assessed bundle producer or summary is invalid')
            try:
                report=validate_assessment_material(self.summary_assessment,self.evidence_spans,self.reading_context,
                    self.summary.to_dict()['draft']['claims'],plan_max_claims=protocol.plan_max_claims,
                    assessor_version=protocol.assessor_version)
                validate_assessment_quality(report,self.summary.to_dict()['draft']['claims'],self.summary.draft.status)
                if (self.versions.prompt!=self.summary.model.prompt_version
                        or self.versions.model!=self.summary.model.model_id
                        or self.quality_status!=('needs_review' if self.summary.draft.status=='needs_review' else 'verified')):
                    raise ValueError('assessed bundle version/quality differs from summary')
            except (ValueError,TypeError,KeyError) as exc:
                raise NarrativeContractError('invalid bundle summary assessment') from exc
        elif self.summary_assessment is not None:
            raise NarrativeContractError('legacy bundle cannot contain summary assessment')
        if self.subject_binding is not None:
            _validate_projection_evidence(
                self.subject_binding, self.evidence_spans, self.selection
            )
        if self.selection.selected_count != len(self.evidence_spans):
            raise NarrativeContractError("bundle selected_count differs from evidence")
        if self.replay.locator_count != len(self.evidence_spans):
            raise NarrativeContractError(
                "bundle replay locator count differs from evidence"
            )
        skipped = self.quality_status == "skipped_no_narrative"
        if skipped and (
            self.selection.status != "skipped_no_narrative"
            or self.evidence_spans
            or self.summary.status != "summary_not_needed"
        ):
            raise NarrativeContractError("skip bundle contains narrative content")
        if not skipped and self.selection.status == "skipped_no_narrative":
            raise NarrativeContractError("non-skip bundle has skipped selection")
        self._validate_summary()

    def _validate_summary(self) -> None:
        if self.summary.status == "summary_not_needed":
            if self.quality_status != "skipped_no_narrative":
                raise NarrativeContractError("only skip bundles may omit summaries")
            return
        if self.summary.status != "completed" or self.summary.draft is None:
            raise NarrativeContractError("unsupported narrative bundle summary status")
        try:
            if isinstance(self.summary.draft, SubjectSummaryDraft):
                validate_subject_summary_draft(
                    self.summary.draft,
                    subject=self.subject,
                    language=self.source_metadata.language,
                    evidence_spans=self.evidence_spans,
                )
            else:
                validate_summary_draft(
                    self.summary.draft,
                    source_id=self.source_ref.source_id,
                    source_sha256=self.source_ref.content_sha256,
                    language=self.source_metadata.language,
                    evidence_spans=self.evidence_spans,
                )
        except SummaryValidationError as exc:
            raise NarrativeContractError(
                "bundle summary does not bind its evidence"
            ) from exc

    def validate_against(
        self, selected: NarrativeSelectResult, summary: NarrativeSummaryResult
    ) -> None:
        summary.validate_against(selected)
        if (
            self.subject != selected.subject
            or self.expected_read_policy_sha256 != selected.expected_read_policy_sha256
            or self.source_metadata != selected.source_metadata
            or self.selection != selected.selection
            or self.evidence_spans != selected.evidence_spans
            or self.reading_context != selected.reading_context
        ):
            raise NarrativeContractError("bundle selection differs from dependency")
        expected_summary = BundleSummaryValue(
            summary.status, summary.translate, summary.draft, summary.model
        )
        if self.summary != expected_summary:
            raise NarrativeContractError("bundle summary differs from dependency")
        if self.transcript_lineage != selected.transcript_lineage or (
            self.transcript_byte_bindings != selected.transcript_byte_bindings
        ):
            raise NarrativeContractError(
                "bundle transcript lineage differs from selection"
            )

    @property
    def subject(self) -> NarrativeSubject:
        return self.subject_binding or NarrativeSubject.from_raw(
            self.source_ref.to_dict()
        )

    @property
    def item_key(self) -> str:
        return (
            self.subject_binding.item_key
            if self.subject_binding is not None
            else self.source_ref.document_id
        )

    def to_dict(self) -> dict[str, Any]:
        value = {
            "schema_version": self.schema_version,
            "source_ref": self.source_ref.to_dict(),
            "expected_read_policy_sha256": self.expected_read_policy_sha256,
            "source_metadata": self.source_metadata.to_dict(),
            "quality_status": self.quality_status,
            "selection": self.selection.to_dict(),
            "evidence_spans": [span.to_dict() for span in self.evidence_spans],
            "summary": self.summary.to_dict(),
            "prompt_review": self.prompt_review.to_dict(),
            "transcript_lineage": self.transcript_lineage.to_dict()
            if self.transcript_lineage
            else None,
            "transcript_byte_bindings": [
                item.to_dict() for item in self.transcript_byte_bindings
            ],
            "versions": self.versions.to_dict(),
            "replay": self.replay.to_dict(),
        }
        if self.reading_context is not None:
            value["reading_context"] = _to_plain(self.reading_context)
        if self.schema_version in {ASSESSED_BUNDLE_SCHEMA,ASSESSED_PROJECTED_BUNDLE_SCHEMA}:
            value['summary_assessment']=_to_plain(self.summary_assessment)
        return _subject_wire(
            value,
            self.subject_binding,
            remove=(
                "source_ref",
                "expected_read_policy_sha256",
                "transcript_lineage",
                "transcript_byte_bindings",
            ),
        )


__all__ = [
    "BUNDLE_MAX_BYTES",
    "SELECT_RESULT_MAX_BYTES",
    "SKIP_BUNDLE_MAX_BYTES",
    "SUMMARY_RESULT_MAX_BYTES",
    "ContractSizeError",
    "NarrativeBundle",
    "NarrativeContractError",
    "NarrativeSelectResult",
    "NarrativeSummaryResult",
    "PhysicalPathLeakError",
    "SourceRevisionEventPayload",
    "assert_no_physical_paths",
]
