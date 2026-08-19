"""Strict v1 evidence-span value objects and deterministic identities."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, fields
from enum import Enum
import hashlib
import json
import math
import re
from types import MappingProxyType
from typing import Any
import unicodedata

from .source_manifest import SOURCE_ID_PREFIX


EVIDENCE_SPAN_SCHEMA_VERSION = "1.0.0"
EVIDENCE_SPAN_ID_PREFIX = "urn:company-wiki:evidence-span:sha256:"

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_SOURCE_ID_RE = re.compile(rf"^{re.escape(SOURCE_ID_PREFIX)}[0-9a-f]{{64}}$")
_SPAN_ID_RE = re.compile(
    rf"^{re.escape(EVIDENCE_SPAN_ID_PREFIX)}[0-9a-f]{{64}}$"
)
_SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z]+(?:[.-][0-9A-Za-z]+)*)?"
    r"(?:\+[0-9A-Za-z]+(?:[.-][0-9A-Za-z]+)*)?$"
)


class EvidenceSpanError(ValueError):
    """Raised when evidence-span data violates the published contract."""


class ParseStatus(str, Enum):
    """Technical extraction status; never a research-review decision."""

    PARSED = "parsed"
    PARTIAL = "partial"
    FAILED = "failed"
    QUARANTINED = "quarantined"


class QualityFlag(str, Enum):
    """Stable v1 extraction-quality vocabulary."""

    OCR_USED = "ocr_used"
    LOW_OCR_CONFIDENCE = "low_ocr_confidence"
    LAYOUT_AMBIGUOUS = "layout_ambiguous"
    TABLE_STRUCTURE_AMBIGUOUS = "table_structure_ambiguous"
    TRUNCATED = "truncated"
    ENCODING_REPAIRED = "encoding_repaired"
    UNIT_INFERRED = "unit_inferred"
    DATE_INFERRED = "date_inferred"
    LOCATOR_UNSTABLE = "locator_unstable"
    PARSER_WARNING = "parser_warning"
    PARSER_ERROR = "parser_error"
    UNSUPPORTED_FORMAT = "unsupported_format"
    PASSWORD_PROTECTED = "password_protected"
    EMPTY_OUTPUT = "empty_output"
    # ZR-502: the PDF first page contradicts the sidecar-declared identity
    # (title/publisher) — review signal, never a research decision.
    HOMEPAGE_IDENTITY_CONTRADICTION = "homepage_identity_contradiction"


def _require_text(value: Any, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be text")
    if not value or value != value.strip():
        raise EvidenceSpanError(f"{field_name} must be non-empty trimmed text")
    if unicodedata.normalize("NFC", value) != value:
        raise EvidenceSpanError(f"{field_name} must use Unicode NFC")
    if any(ord(char) < 32 for char in value):
        raise EvidenceSpanError(f"{field_name} must not contain control characters")
    return value


def _require_sha256(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise EvidenceSpanError(
            f"{field_name} must be a lowercase 64-character SHA-256"
        )
    return value


def _require_source_id(value: Any) -> str:
    if not isinstance(value, str) or not _SOURCE_ID_RE.fullmatch(value):
        raise EvidenceSpanError("source_id must be a source-manifest SHA-256 URN")
    return value


def _require_semver(value: Any) -> str:
    value = _require_text(value, "parser_version")
    if not _SEMVER_RE.fullmatch(value):
        raise EvidenceSpanError("parser_version must be semantic version text")
    return value


def _require_nfc_json_text(value: str, field_name: str) -> str:
    if unicodedata.normalize("NFC", value) != value:
        raise EvidenceSpanError(f"{field_name} must use Unicode NFC")
    return value


def _freeze_json(value: Any, field_name: str = "structured_value") -> Any:
    """Validate a deterministic JSON value and recursively freeze containers."""

    if value is None or isinstance(value, bool) or isinstance(value, int):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise EvidenceSpanError(f"{field_name} must not contain NaN or Infinity")
        return value
    if isinstance(value, str):
        return _require_nfc_json_text(value, field_name)
    if isinstance(value, Mapping):
        frozen: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError(f"{field_name} object keys must be text")
            _require_nfc_json_text(key, f"{field_name} key")
            frozen[key] = _freeze_json(item, f"{field_name}.{key}")
        return MappingProxyType(frozen)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return tuple(
            _freeze_json(item, f"{field_name}[{index}]")
            for index, item in enumerate(value)
        )
    raise TypeError(f"{field_name} must contain only JSON values")


def _plain_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _plain_json(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_plain_json(item) for item in value]
    return value


def _canonical_json(value: Any) -> str:
    return json.dumps(
        _plain_json(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _canonical_sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def output_sha256_for(*, raw_text: str | None, structured_value: Any) -> str:
    if raw_text is not None:
        if not isinstance(raw_text, str):
            raise TypeError("raw_text must be text or null")
        _require_nfc_json_text(raw_text, "raw_text")
    frozen_value = _freeze_json(structured_value)
    return _canonical_sha256(
        {
            "raw_text": raw_text,
            "structured_value": frozen_value,
        }
    )


def evidence_span_id_for(
    *, source_id: str, locator: str, output_sha256: str
) -> str:
    source_id = _require_source_id(source_id)
    locator = _require_text(locator, "locator")
    output_sha256 = _require_sha256(output_sha256, "output_sha256")
    digest = _canonical_sha256(
        {
            "locator": locator,
            "output_sha256": output_sha256,
            "source_id": source_id,
        }
    )
    return EVIDENCE_SPAN_ID_PREFIX + digest


def _normalize_quality_flags(value: Any) -> tuple[str, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise TypeError("quality_flags must be an array")
    normalized: set[str] = set()
    for item in value:
        try:
            normalized.add(QualityFlag(item).value)
        except (TypeError, ValueError) as exc:
            raise EvidenceSpanError(f"quality_flags contains invalid value: {item!r}") from exc
    return tuple(sorted(normalized))


@dataclass(frozen=True)
class EvidenceCoordinates:
    """A strict structural location in one normalized immutable source."""

    page_number: int | None = None
    paragraph_index: int | None = None
    table_index: int | None = None
    row_index: int | None = None
    column_index: int | None = None
    char_start: int | None = None
    char_end: int | None = None

    def __post_init__(self) -> None:
        for field_name in (
            "page_number",
            "paragraph_index",
            "table_index",
            "row_index",
            "column_index",
            "char_start",
            "char_end",
        ):
            value = getattr(self, field_name)
            if value is None:
                continue
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f"{field_name} must be an integer or null")
            minimum = 1 if field_name == "page_number" else 0
            if value < minimum:
                raise EvidenceSpanError(f"{field_name} must be >= {minimum}")

        if all(getattr(self, field.name) is None for field in fields(self)):
            raise EvidenceSpanError("coordinates must contain at least one location")
        if (self.char_start is None) != (self.char_end is None):
            raise EvidenceSpanError("char_start and char_end must be supplied together")
        if self.char_start is not None and self.char_end <= self.char_start:
            raise EvidenceSpanError("char_end must be greater than char_start")
        if (self.row_index is not None or self.column_index is not None) and (
            self.table_index is None
        ):
            raise EvidenceSpanError("row_index and column_index require table_index")
        if self.paragraph_index is not None and self.table_index is not None:
            raise EvidenceSpanError("paragraph and table coordinates are mutually exclusive")

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "EvidenceCoordinates":
        if not isinstance(data, Mapping):
            raise TypeError("coordinates must be an object")
        known = {field.name for field in fields(cls)}
        supplied = set(data)
        unknown = supplied - known
        if unknown:
            raise EvidenceSpanError(
                f"coordinate unknown fields: {sorted(unknown)}"
            )
        missing = known - supplied
        if missing:
            raise EvidenceSpanError(
                f"coordinate missing fields: {sorted(missing)}"
            )
        return cls(**dict(data))

    def to_dict(self) -> dict[str, int | None]:
        return {
            "page_number": self.page_number,
            "paragraph_index": self.paragraph_index,
            "table_index": self.table_index,
            "row_index": self.row_index,
            "column_index": self.column_index,
            "char_start": self.char_start,
            "char_end": self.char_end,
        }

    def locator(self) -> str:
        parts = ["loc:v1"]
        ordered = (
            ("page", self.page_number),
            ("paragraph", self.paragraph_index),
            ("table", self.table_index),
            ("row", self.row_index),
            ("column", self.column_index),
        )
        parts.extend(f"{name}:{value}" for name, value in ordered if value is not None)
        if self.char_start is not None:
            parts.append(f"chars:{self.char_start}-{self.char_end}")
        return "/".join(parts)


@dataclass(frozen=True)
class EvidenceSpan:
    """One deterministic parser result bound to an immutable source location."""

    schema_version: str
    span_id: str
    source_id: str
    locator: str
    coordinates: EvidenceCoordinates
    raw_text: str | None
    structured_value: Any
    parser_name: str
    parser_version: str
    output_sha256: str
    parse_status: ParseStatus
    quality_flags: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.schema_version != EVIDENCE_SPAN_SCHEMA_VERSION:
            raise EvidenceSpanError(
                f"schema_version must be {EVIDENCE_SPAN_SCHEMA_VERSION}"
            )
        if not isinstance(self.span_id, str) or not _SPAN_ID_RE.fullmatch(self.span_id):
            raise EvidenceSpanError("span_id must be the canonical SHA-256 URN")
        source_id = _require_source_id(self.source_id)
        if not isinstance(self.coordinates, EvidenceCoordinates):
            raise TypeError("coordinates must be EvidenceCoordinates")

        expected_locator = self.coordinates.locator()
        if self.locator != expected_locator:
            raise EvidenceSpanError("locator must match coordinates")

        raw_text = self.raw_text
        if raw_text is not None:
            if not isinstance(raw_text, str):
                raise TypeError("raw_text must be text or null")
            _require_nfc_json_text(raw_text, "raw_text")
        frozen_value = _freeze_json(self.structured_value)
        object.__setattr__(self, "structured_value", frozen_value)

        object.__setattr__(self, "parser_name", _require_text(self.parser_name, "parser_name"))
        object.__setattr__(self, "parser_version", _require_semver(self.parser_version))
        try:
            status = ParseStatus(self.parse_status)
        except (TypeError, ValueError) as exc:
            raise EvidenceSpanError("parse_status is invalid") from exc
        object.__setattr__(self, "parse_status", status)
        flags = _normalize_quality_flags(self.quality_flags)
        object.__setattr__(self, "quality_flags", flags)

        expected_output = output_sha256_for(
            raw_text=raw_text,
            structured_value=frozen_value,
        )
        _require_sha256(self.output_sha256, "output_sha256")
        if self.output_sha256 != expected_output:
            raise EvidenceSpanError("output_sha256 must match parser output")

        expected_span_id = evidence_span_id_for(
            source_id=source_id,
            locator=expected_locator,
            output_sha256=expected_output,
        )
        if self.span_id != expected_span_id:
            raise EvidenceSpanError("span_id must match source, locator, and output")

        has_output = raw_text is not None or frozen_value is not None
        if status is ParseStatus.PARSED and not has_output:
            raise EvidenceSpanError("parsed evidence must contain parser output")
        if status is ParseStatus.PARTIAL and (not has_output or not flags):
            raise EvidenceSpanError(
                "partial evidence must contain output and quality_flags"
            )
        if status is ParseStatus.FAILED and (has_output or not flags):
            raise EvidenceSpanError(
                "failed evidence must contain no output and at least one quality flag"
            )
        if status is ParseStatus.QUARANTINED and not flags:
            raise EvidenceSpanError("quarantined evidence must contain quality_flags")

    @classmethod
    def create(
        cls,
        *,
        source_id: str,
        coordinates: EvidenceCoordinates,
        raw_text: str | None,
        structured_value: Any,
        parser_name: str,
        parser_version: str,
        parse_status: ParseStatus | str,
        quality_flags: Sequence[QualityFlag | str],
    ) -> "EvidenceSpan":
        if not isinstance(coordinates, EvidenceCoordinates):
            raise TypeError("coordinates must be EvidenceCoordinates")
        frozen_value = _freeze_json(structured_value)
        output_sha256 = output_sha256_for(
            raw_text=raw_text,
            structured_value=frozen_value,
        )
        locator = coordinates.locator()
        return cls(
            schema_version=EVIDENCE_SPAN_SCHEMA_VERSION,
            span_id=evidence_span_id_for(
                source_id=source_id,
                locator=locator,
                output_sha256=output_sha256,
            ),
            source_id=source_id,
            locator=locator,
            coordinates=coordinates,
            raw_text=raw_text,
            structured_value=frozen_value,
            parser_name=parser_name,
            parser_version=parser_version,
            output_sha256=output_sha256,
            parse_status=parse_status,
            quality_flags=_normalize_quality_flags(quality_flags),
        )

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "EvidenceSpan":
        if not isinstance(data, Mapping):
            raise TypeError("evidence span input must be an object")
        known = {field.name for field in fields(cls)}
        supplied = set(data)
        unknown = supplied - known
        if unknown:
            raise EvidenceSpanError(f"evidence span unknown fields: {sorted(unknown)}")
        missing = known - supplied
        if missing:
            raise EvidenceSpanError(f"evidence span missing fields: {sorted(missing)}")

        prepared = dict(data)
        prepared["coordinates"] = EvidenceCoordinates.from_dict(prepared["coordinates"])
        raw_flags = prepared["quality_flags"]
        if isinstance(raw_flags, (str, bytes)) or not isinstance(raw_flags, Sequence):
            raise TypeError("quality_flags must be an array")
        if len(raw_flags) != len(set(raw_flags)):
            raise EvidenceSpanError("quality_flags must not contain duplicates")
        return cls(**prepared)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "span_id": self.span_id,
            "source_id": self.source_id,
            "locator": self.locator,
            "coordinates": self.coordinates.to_dict(),
            "raw_text": self.raw_text,
            "structured_value": _plain_json(self.structured_value),
            "parser_name": self.parser_name,
            "parser_version": self.parser_version,
            "output_sha256": self.output_sha256,
            "parse_status": self.parse_status.value,
            "quality_flags": list(self.quality_flags),
        }

    def canonical_json(self) -> str:
        return _canonical_json(self.to_dict())

