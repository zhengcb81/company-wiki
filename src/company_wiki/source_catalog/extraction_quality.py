"""Deterministic, read-only extraction-quality diagnostics."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
import json
from pathlib import Path
import re
import sqlite3
from typing import Any, Iterator

from company_wiki.source_contract import (
    EvidenceSpan,
    EvidenceSpanError,
    ParseStatus,
    QualityFlag,
)
from company_wiki.source_contract.source_manifest import SOURCE_ID_PREFIX

from .models import NORMALIZER_VERSION


EXTRACTION_QUALITY_SCHEMA_VERSION = "1.0.0"
MAX_QUALITY_LOCATOR_REFERENCES = 500

_NORMALIZER_NAME = "source_catalog_normalizer"
_SOURCE_ID_RE = re.compile(rf"^{re.escape(SOURCE_ID_PREFIX)}[0-9a-f]{{64}}$")
_DOCUMENT_ID_RE = re.compile(
    r"^urn:company-wiki:document:sha256:[0-9a-f]{64}$"
)
_SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)
_SOURCE_STATUSES = frozenset(
    {"active", "incomplete", "quarantined", "upstream_rejected"}
)
_ARTIFACT_STATUSES = frozenset({"completed", "partial", "unsupported", "failed"})
_BENIGN_QUALITY_FLAGS = frozenset({QualityFlag.OCR_USED.value})
class ExtractionQualityState(str, Enum):
    """Document-level technical extraction state; never an investment decision."""

    USABLE = "usable"
    REVIEW_REQUIRED = "review_required"
    UNAVAILABLE = "unavailable"


class ExtractionQualityError(ValueError):
    """Base error for extraction-quality diagnostics."""


class ExtractionQualityInputError(ExtractionQualityError):
    """Raised when an identity or locator bound is invalid."""


class ExtractionQualityUnavailableError(ExtractionQualityError):
    """Raised when the catalog cannot be opened without writes."""


class ExtractionQualityNotFoundError(ExtractionQualityError):
    """Raised when an exact source or document identity is unknown."""


class ExtractionQualityAmbiguousError(ExtractionQualityError):
    """Raised when one source identity resolves to multiple documents."""


class ExtractionQualityIntegrityError(ExtractionQualityError):
    """Raised when persisted extraction data violates its canonical contract."""


@dataclass(frozen=True)
class ExtractionLocatorReference:
    """Body-free reference to one validated EvidenceSpan."""

    span_id: str
    locator: str
    parse_status: str
    quality_flags: tuple[str, ...]
    parser_name: str
    parser_version: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "span_id": self.span_id,
            "locator": self.locator,
            "parse_status": self.parse_status,
            "quality_flags": list(self.quality_flags),
            "parser_name": self.parser_name,
            "parser_version": self.parser_version,
        }


@dataclass(frozen=True)
class ExtractionQualityReport:
    """Immutable, source-only extraction diagnostic result."""

    quality_state: ExtractionQualityState
    reason_codes: tuple[str, ...]
    document_id: str
    source_id: str | None
    source_status: str
    content_sha256: str | None
    byte_size: int | None
    mime_type: str | None
    location_status_counts: tuple[tuple[str, int], ...]
    artifact_status: str | None
    parser_names: tuple[str, ...]
    parser_versions: tuple[str, ...]
    quality_flags: tuple[str, ...]
    recorded_span_count: int | None
    span_count: int
    usable_output_span_count: int
    parsed_count: int
    partial_count: int
    failed_count: int
    quarantined_count: int
    locator_limit: int
    locator_references: tuple[ExtractionLocatorReference, ...]

    def to_dict(self) -> dict[str, Any]:
        location_counts = dict(self.location_status_counts)
        return {
            "schema_version": EXTRACTION_QUALITY_SCHEMA_VERSION,
            "quality_state": self.quality_state.value,
            "reason_codes": list(self.reason_codes),
            "identity": {
                "document_id": self.document_id,
                "source_id": self.source_id,
            },
            "source": {
                "source_id": self.source_id,
                "source_status": self.source_status,
                "content_sha256": self.content_sha256,
                "byte_size": self.byte_size,
                "mime_type": self.mime_type,
                "active_location_count": location_counts.get("active", 0),
                "total_location_count": sum(location_counts.values()),
                "location_status_counts": location_counts,
            },
            "normalization": {
                "artifact_status": self.artifact_status,
                "generator_name": _NORMALIZER_NAME,
                "generator_version": NORMALIZER_VERSION,
                "parser_names": list(self.parser_names),
                "parser_versions": list(self.parser_versions),
                "quality_flags": list(self.quality_flags),
                "recorded_span_count": self.recorded_span_count,
            },
            "counts": {
                "spans": self.span_count,
                "usable_output_spans": self.usable_output_span_count,
                "parsed": self.parsed_count,
                "partial": self.partial_count,
                "failed": self.failed_count,
                "quarantined": self.quarantined_count,
            },
            "locator_limit": self.locator_limit,
            "locator_references_truncated": (
                self.span_count > len(self.locator_references)
            ),
            "locator_references": [
                item.to_dict() for item in self.locator_references
            ],
        }


def _validate_source_id(value: Any) -> str:
    if not isinstance(value, str) or not _SOURCE_ID_RE.fullmatch(value):
        raise ExtractionQualityInputError(
            "source_id must be the canonical SHA-256 URN"
        )
    return value


def _validate_document_id(value: Any) -> str:
    if not isinstance(value, str) or not _DOCUMENT_ID_RE.fullmatch(value):
        raise ExtractionQualityInputError(
            "document_id must be the canonical document SHA-256 URN"
        )
    return value


def _validate_locator_limit(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ExtractionQualityInputError("locator_limit must be an integer")
    if value <= 0 or value > MAX_QUALITY_LOCATOR_REFERENCES:
        raise ExtractionQualityInputError(
            f"locator_limit must be in [1, {MAX_QUALITY_LOCATOR_REFERENCES}]"
        )
    return value


def _artifact_metadata(value: str) -> dict[str, Any]:
    try:
        payload = json.loads(value)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ExtractionQualityIntegrityError(
            "normalized artifact metadata is not valid JSON"
        ) from exc
    if not isinstance(payload, dict):
        raise ExtractionQualityIntegrityError(
            "normalized artifact metadata must be an object"
        )
    required = {"parser_name", "parser_version", "quality_flags", "span_count"}
    if not required <= payload.keys():
        raise ExtractionQualityIntegrityError(
            "normalized artifact metadata is missing quality fields"
        )
    parser_name = payload["parser_name"]
    parser_version = payload["parser_version"]
    span_count = payload["span_count"]
    if not isinstance(parser_name, str) or not parser_name.strip():
        raise ExtractionQualityIntegrityError("artifact parser_name is invalid")
    if not isinstance(parser_version, str) or not _SEMVER_RE.fullmatch(parser_version):
        raise ExtractionQualityIntegrityError("artifact parser_version is invalid")
    if isinstance(span_count, bool) or not isinstance(span_count, int) or span_count < 0:
        raise ExtractionQualityIntegrityError("artifact span_count is invalid")
    raw_flags = payload["quality_flags"]
    if not isinstance(raw_flags, list):
        raise ExtractionQualityIntegrityError("artifact quality_flags must be an array")
    try:
        flags = tuple(sorted(QualityFlag(item).value for item in raw_flags))
    except (TypeError, ValueError) as exc:
        raise ExtractionQualityIntegrityError(
            "artifact quality_flags contains an unknown flag"
        ) from exc
    if len(flags) != len(set(flags)):
        raise ExtractionQualityIntegrityError(
            "artifact quality_flags contains duplicates"
        )
    return {
        "parser_name": parser_name,
        "parser_version": parser_version,
        "quality_flags": flags,
        "span_count": span_count,
    }


class ExtractionQualityService:
    """Assess existing catalog extraction metadata through enforced read-only SQL."""

    def __init__(self, database_path: Path):
        if not isinstance(database_path, Path):
            raise TypeError("database_path must be pathlib.Path")
        self.database_path = database_path

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        if not self.database_path.is_file():
            raise ExtractionQualityUnavailableError(
                "source catalog database is unavailable"
            )
        wal_path = Path(str(self.database_path) + "-wal")
        shm_path = Path(str(self.database_path) + "-shm")
        if wal_path.exists() and not shm_path.is_file():
            raise ExtractionQualityUnavailableError(
                "source catalog WAL cannot be read without existing shared memory"
            )
        uri = self.database_path.resolve().as_uri() + "?mode=ro"
        if not wal_path.exists():
            uri += "&immutable=1"
        connection: sqlite3.Connection | None = None
        try:
            connection = sqlite3.connect(uri, uri=True, timeout=5.0)
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA query_only=ON")
            connection.execute("PRAGMA busy_timeout=5000")
            yield connection
        except ExtractionQualityError:
            raise
        except (OSError, sqlite3.Error) as exc:
            raise ExtractionQualityUnavailableError(
                f"source catalog read failed: {type(exc).__name__}: {str(exc)[:500]}"
            ) from exc
        finally:
            if connection is not None:
                connection.close()

    @staticmethod
    def _document(
        connection: sqlite3.Connection,
        *,
        source_id: str | None,
        document_id: str | None,
    ) -> sqlite3.Row:
        select = """SELECT d.document_id,d.primary_source_id,d.source_status,
            s.content_sha256,s.byte_size,s.mime_type
            FROM documents d LEFT JOIN sources s ON s.source_id=d.primary_source_id"""
        if source_id is not None:
            rows = connection.execute(
                select + " WHERE d.primary_source_id=? ORDER BY d.document_id LIMIT 2",
                (source_id,),
            ).fetchall()
            if not rows:
                raise ExtractionQualityNotFoundError(
                    "no document matches the exact source identity"
                )
            if len(rows) > 1:
                raise ExtractionQualityAmbiguousError(
                    "source identity maps to multiple documents"
                )
            row = rows[0]
        else:
            row = connection.execute(
                select + " WHERE d.document_id=?",
                (document_id,),
            ).fetchone()
            if row is None:
                raise ExtractionQualityNotFoundError(
                    "no document matches the exact document identity"
                )
        if row["source_status"] not in _SOURCE_STATUSES:
            raise ExtractionQualityIntegrityError(
                "document source_status is outside the canonical vocabulary"
            )
        if row["primary_source_id"] is not None:
            expected = SOURCE_ID_PREFIX + str(row["content_sha256"])
            if row["primary_source_id"] != expected:
                raise ExtractionQualityIntegrityError(
                    "document primary source conflicts with source content hash"
                )
        return row

    @staticmethod
    def _location_counts(
        connection: sqlite3.Connection, *, document_id: str, source_id: str | None
    ) -> tuple[tuple[str, int], ...]:
        if source_id is None:
            rows = connection.execute(
                """SELECT location_status,COUNT(*) AS count FROM locations
                WHERE document_id=? GROUP BY location_status ORDER BY location_status""",
                (document_id,),
            ).fetchall()
        else:
            rows = connection.execute(
                """SELECT location_status,COUNT(*) AS count FROM locations
                WHERE document_id=? AND source_id=?
                GROUP BY location_status ORDER BY location_status""",
                (document_id, source_id),
            ).fetchall()
        return tuple((str(row["location_status"]), int(row["count"])) for row in rows)

    @staticmethod
    def _artifact(
        connection: sqlite3.Connection, *, document_id: str, source_id: str | None
    ) -> tuple[str | None, dict[str, Any] | None]:
        rows = connection.execute(
            """SELECT source_id,status,metadata_json FROM artifacts
            WHERE document_id=? AND artifact_role='normalized'
            AND generator_name=? AND generator_version=? LIMIT 2""",
            (document_id, _NORMALIZER_NAME, NORMALIZER_VERSION),
        ).fetchall()
        if not rows:
            return None, None
        if len(rows) != 1:
            raise ExtractionQualityIntegrityError(
                "multiple current normalized artifacts exist"
            )
        row = rows[0]
        if row["source_id"] != source_id:
            raise ExtractionQualityIntegrityError(
                "normalized artifact source conflicts with document identity"
            )
        status = str(row["status"])
        if status not in _ARTIFACT_STATUSES:
            raise ExtractionQualityIntegrityError(
                "normalized artifact status is outside the canonical vocabulary"
            )
        return status, _artifact_metadata(row["metadata_json"])

    @staticmethod
    def _spans(
        connection: sqlite3.Connection,
        *,
        document_id: str,
        source_id: str | None,
    ) -> tuple[EvidenceSpan, ...]:
        rows = connection.execute(
            """SELECT span_id,source_id,locator,raw_text,span_json,
            parser_name,parser_version,parse_status FROM evidence_spans
            WHERE document_id=? ORDER BY locator,span_id""",
            (document_id,),
        ).fetchall()
        spans = []
        for row in rows:
            try:
                span = EvidenceSpan.from_dict(json.loads(row["span_json"]))
            except (json.JSONDecodeError, EvidenceSpanError, TypeError, ValueError) as exc:
                raise ExtractionQualityIntegrityError(
                    f"persisted span failed canonical validation: {type(exc).__name__}"
                ) from exc
            expected = (
                row["span_id"],
                row["source_id"],
                row["locator"],
                row["raw_text"],
                row["parser_name"],
                row["parser_version"],
                row["parse_status"],
            )
            actual = (
                span.span_id,
                span.source_id,
                span.locator,
                span.raw_text,
                span.parser_name,
                span.parser_version,
                span.parse_status.value,
            )
            if actual != expected or span.source_id != source_id:
                raise ExtractionQualityIntegrityError(
                    "persisted span conflicts with catalog identity columns"
                )
            spans.append(span)
        return tuple(spans)

    @staticmethod
    def _validate_aggregate(
        *,
        artifact_status: str | None,
        metadata: dict[str, Any] | None,
        spans: tuple[EvidenceSpan, ...],
    ) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...], int | None]:
        parser_names = tuple(sorted({span.parser_name for span in spans}))
        parser_versions = tuple(sorted({span.parser_version for span in spans}))
        span_flags = tuple(sorted({flag for span in spans for flag in span.quality_flags}))
        if metadata is None:
            return parser_names, parser_versions, span_flags, None
        recorded_count = int(metadata["span_count"])
        if recorded_count != len(spans):
            raise ExtractionQualityIntegrityError(
                "normalized artifact span_count conflicts with evidence rows"
            )
        artifact_flags = tuple(metadata["quality_flags"])
        if spans:
            if artifact_flags != span_flags:
                raise ExtractionQualityIntegrityError(
                    "normalized artifact flags conflict with evidence rows"
                )
            if parser_names != (metadata["parser_name"],) or parser_versions != (
                metadata["parser_version"],
            ):
                raise ExtractionQualityIntegrityError(
                    "normalized artifact parser conflicts with evidence rows"
                )
        elif artifact_status not in {"unsupported", "failed"} and artifact_flags:
            raise ExtractionQualityIntegrityError(
                "zero-span artifact contains unexpected quality flags"
            )
        if artifact_status == "completed" and any(
            span.parse_status is not ParseStatus.PARSED for span in spans
        ):
            raise ExtractionQualityIntegrityError(
                "completed artifact contains non-parsed evidence"
            )
        return (
            parser_names or (metadata["parser_name"],),
            parser_versions or (metadata["parser_version"],),
            artifact_flags,
            recorded_count,
        )

    def assess(
        self,
        *,
        source_id: str | None = None,
        document_id: str | None = None,
        locator_limit: int = 100,
    ) -> ExtractionQualityReport:
        if (source_id is None) == (document_id is None):
            raise ExtractionQualityInputError(
                "exactly one of source_id or document_id is required"
            )
        source_id = _validate_source_id(source_id) if source_id is not None else None
        document_id = (
            _validate_document_id(document_id) if document_id is not None else None
        )
        locator_limit = _validate_locator_limit(locator_limit)

        with self._connection() as connection:
            document = self._document(
                connection, source_id=source_id, document_id=document_id
            )
            resolved_document_id = str(document["document_id"])
            resolved_source_id = document["primary_source_id"]
            locations = self._location_counts(
                connection,
                document_id=resolved_document_id,
                source_id=resolved_source_id,
            )
            artifact_status, metadata = self._artifact(
                connection,
                document_id=resolved_document_id,
                source_id=resolved_source_id,
            )
            spans = self._spans(
                connection,
                document_id=resolved_document_id,
                source_id=resolved_source_id,
            )
            parser_names, parser_versions, flags, recorded_count = (
                self._validate_aggregate(
                    artifact_status=artifact_status,
                    metadata=metadata,
                    spans=spans,
                )
            )

        status_counts = {status: 0 for status in ParseStatus}
        for span in spans:
            status_counts[span.parse_status] += 1
        usable_output = sum(
            1
            for span in spans
            if span.parse_status in {ParseStatus.PARSED, ParseStatus.PARTIAL}
        )
        location_map = dict(locations)
        unavailable_reasons: list[str] = []
        review_reasons: list[str] = []
        source_status = str(document["source_status"])
        if source_status == "quarantined":
            unavailable_reasons.append("source_quarantined")
        elif source_status == "upstream_rejected":
            unavailable_reasons.append("source_upstream_rejected")
        elif source_status == "incomplete":
            review_reasons.append("source_incomplete")
        if location_map.get("active", 0) == 0:
            unavailable_reasons.append("no_active_source_location")
        if artifact_status is None:
            unavailable_reasons.append("normalization_pending")
        elif artifact_status == "unsupported":
            unavailable_reasons.append("normalization_unsupported")
        elif artifact_status == "failed":
            unavailable_reasons.append("normalization_failed")
        elif artifact_status == "partial":
            review_reasons.append("normalization_partial")
        if usable_output == 0:
            unavailable_reasons.append("no_usable_evidence")
        if status_counts[ParseStatus.PARTIAL]:
            review_reasons.append("partial_evidence")
        if status_counts[ParseStatus.FAILED]:
            review_reasons.append("failed_evidence")
        if status_counts[ParseStatus.QUARANTINED]:
            review_reasons.append("quarantined_evidence")
        if usable_output and set(flags) - _BENIGN_QUALITY_FLAGS:
            review_reasons.append("quality_flags_require_review")

        if unavailable_reasons:
            state = ExtractionQualityState.UNAVAILABLE
        elif review_reasons:
            state = ExtractionQualityState.REVIEW_REQUIRED
        else:
            state = ExtractionQualityState.USABLE
        reasons = tuple(unavailable_reasons + review_reasons)
        references = tuple(
            ExtractionLocatorReference(
                span_id=span.span_id,
                locator=span.locator,
                parse_status=span.parse_status.value,
                quality_flags=span.quality_flags,
                parser_name=span.parser_name,
                parser_version=span.parser_version,
            )
            for span in spans[:locator_limit]
        )
        return ExtractionQualityReport(
            quality_state=state,
            reason_codes=reasons,
            document_id=resolved_document_id,
            source_id=resolved_source_id,
            source_status=source_status,
            content_sha256=document["content_sha256"],
            byte_size=document["byte_size"],
            mime_type=document["mime_type"],
            location_status_counts=locations,
            artifact_status=artifact_status,
            parser_names=parser_names,
            parser_versions=parser_versions,
            quality_flags=flags,
            recorded_span_count=recorded_count,
            span_count=len(spans),
            usable_output_span_count=usable_output,
            parsed_count=status_counts[ParseStatus.PARSED],
            partial_count=status_counts[ParseStatus.PARTIAL],
            failed_count=status_counts[ParseStatus.FAILED],
            quarantined_count=status_counts[ParseStatus.QUARANTINED],
            locator_limit=locator_limit,
            locator_references=references,
        )


__all__ = [
    "EXTRACTION_QUALITY_SCHEMA_VERSION",
    "MAX_QUALITY_LOCATOR_REFERENCES",
    "ExtractionLocatorReference",
    "ExtractionQualityAmbiguousError",
    "ExtractionQualityError",
    "ExtractionQualityInputError",
    "ExtractionQualityIntegrityError",
    "ExtractionQualityNotFoundError",
    "ExtractionQualityReport",
    "ExtractionQualityService",
    "ExtractionQualityState",
    "ExtractionQualityUnavailableError",
]
def detect_orphan_spans(store: Any) -> list[dict[str, Any]]:
    """Return evidence_spans whose source_id no longer exists in the sources table.

    CW-2 quality gate: orphaned spans indicate a source was deleted or a span
    was written with a non-existent source_id. This should never occur under
    normal operation (sources are immutable), but defensive detection helps
    catch catalog corruption or manual cleanup errors.
    """
    sql = """SELECT s.span_id, s.source_id, s.locator, s.parser_name,
                    s.parser_version, s.parse_status, s.quality_flags
             FROM evidence_spans s
             WHERE s.source_id NOT IN (SELECT source_id FROM sources)"""
    rows = store.fetchall(sql)
    return [dict(r) for r in rows]


def detect_locator_drift(
    store: Any,
    *,
    parser_name: str,
    min_span_count: int = 5,
) -> list[dict[str, Any]]:
    """Detect documents whose span count changed significantly between parser
    versions — a sign of locator drift or parser regression.

    CW-2 quality gate: when a new parser version changes the number of spans
    for the same source, it may indicate that page/paragraph locators have
    shifted, making dependent evidence lookups unreliable.
    """
    sql = """SELECT source_id, parser_version, COUNT(*) AS span_count,
                    MIN(created_at) AS first_seen
             FROM evidence_spans
             WHERE parser_name = ?
             GROUP BY source_id, parser_version
             HAVING span_count >= ?"""
    rows = store.fetchall(sql, (parser_name, min_span_count))
    from collections import defaultdict

    by_source: dict[str, list] = defaultdict(list)
    for r in rows:
        by_source[r["source_id"]].append(dict(r))
    drifted = []
    for source_id, versions in by_source.items():
        if len(versions) <= 1:
            continue
        counts = [v["span_count"] for v in versions]
        if max(counts) - min(counts) > max(3, min(counts) * 0.3):
            drifted.append(
                {
                    "source_id": source_id,
                    "versions": versions,
                    "count_range": [min(counts), max(counts)],
                }
            )
    return drifted
