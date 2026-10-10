"""Strict, pathless contracts for the three narrative automation jobs."""

from __future__ import annotations

import re
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

from .models import canonical_json, canonical_json_hash


SOURCE_REVISION_EVENT_SCHEMA = "source-revision-event/2.0"
PROJECTED_SOURCE_REVISION_EVENT_SCHEMA = "source-revision-event/3.0"
SELECT_RESULT_SCHEMA = "narrative-select-result/2.0"
PROJECTED_SELECT_RESULT_SCHEMA = "narrative-select-result/3.0"
SUMMARY_RESULT_SCHEMA = "narrative-summary-result/2.0"
PROJECTED_SUMMARY_RESULT_SCHEMA = "narrative-summary-result/3.0"
BUNDLE_SCHEMA = "narrative-bundle/2.0"
PROJECTED_BUNDLE_SCHEMA = "narrative-bundle/3.0"
SELECT_RESULT_MAX_BYTES = 1024 * 1024
SUMMARY_RESULT_MAX_BYTES = 64 * 1024
BUNDLE_MAX_BYTES = 1280 * 1024
SKIP_BUNDLE_MAX_BYTES = 16 * 1024

_SHA = re.compile(r"[0-9a-f]{64}\Z")
_DRIVE_PATH = re.compile(r"[A-Za-z]:[\\/]")
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

    @classmethod
    def from_dict(cls, value: object) -> "NarrativeSelectResult":
        assert_no_physical_paths(value)
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
            and value.get("schema_version") == PROJECTED_SELECT_RESULT_SCHEMA
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
        item = _exact(value, keys, "narrative select result")
        if item["schema_version"] not in {
            SELECT_RESULT_SCHEMA,
            PROJECTED_SELECT_RESULT_SCHEMA,
        }:
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
        {"claim_id", "text", "evidence_ids", "claim_type", "modality", "needs_review"},
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


def _draft_to_dict(value: SourceSummaryDraft) -> dict[str, Any]:
    return {
        "source_id": value.source_id,
        "source_sha256": value.source_sha256,
        "language": value.language,
        "claims": [
            {
                "claim_id": claim.claim_id,
                "text": claim.text,
                "evidence_ids": list(claim.evidence_ids),
                "claim_type": claim.claim_type,
                "modality": claim.modality,
                "needs_review": claim.needs_review,
            }
            for claim in value.claims
        ],
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
        "claims": [
            {
                "claim_id": c.claim_id,
                "text": c.text,
                "evidence_ids": list(c.evidence_ids),
                "claim_type": c.claim_type,
                "modality": c.modality,
                "needs_review": c.needs_review,
            }
            for c in value.claims
        ],
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

    @classmethod
    def from_dict(cls, value: object) -> "NarrativeBundle":
        assert_no_physical_paths(value)
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
            and value.get("schema_version") == PROJECTED_BUNDLE_SCHEMA
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
        item = _exact(value, keys, "narrative bundle")
        if item["schema_version"] not in {BUNDLE_SCHEMA, PROJECTED_BUNDLE_SCHEMA}:
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
