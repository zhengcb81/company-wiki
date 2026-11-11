"""Parser-owner API for verified processed-document inputs.

This module owns format routing, parser staging, isolated parser execution and
the parser result projection consumed by the pathless processed-document
endpoint. Source lookup and byte verification remain with SourceVersionPort.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
import json
import logging
import tempfile
from pathlib import Path
from typing import Any, BinaryIO, Protocol

from company_wiki.canonical_ingest import ParserResult
from company_wiki.document_normalization import (
    PARSER_NAME as DN_PARSER_NAME,
    NormalizationError,
    NormalizationLimits,
    UnsupportedFormatError,
    normalize_verified_document,
)
from company_wiki.source_contract import (
    EvidenceCoordinates,
    ParseStatus,
    SourceChunkSink,
    SourceChunkSinkError,
    SourceProcessingDescriptor,
    SourceReadError,
    VerifiedContent,
    VerifiedVersionReceipt,
    plain_json_value,
)

from .normalizer import (
    NormalizationCancelledError,
    NormalizationTimeoutError,
    NormalizedDocument,
    ParserProcessError,
    UnsupportedDocumentError,
    escape_table_cell,
    run_parser_isolated,
    unsupported_result,
)

PROCESSED_DIRECT_FORMATS = {
    ".docx": frozenset({
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }),
    ".html": frozenset({"text/html", "application/xhtml+xml"}),
    ".htm": frozenset({"text/html", "application/xhtml+xml"}),
    ".pptx": frozenset({
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "application/vnd.openxmlformats-officedocument.presentationml.slideshow",
    }),
}
_PARSER_TIMEOUT_SECONDS = 3600.0
_PARSER_HEARTBEAT_SECONDS = 15.0
_PARSER_RESULT_MAX_BYTES = 268_435_456
_LOGGER = logging.getLogger(__name__)
_STATUS_BY_CATALOG_STATUS = {
    "completed": "complete",
    "partial": "partial",
    "unsupported": "unsupported",
}


@dataclass(frozen=True)
class ProcessedParseOutcome:
    """Parser result in the stable unit vocabulary used by the endpoint."""

    parser_name: str
    parser_version: str
    status: str
    quality_flags: tuple[str, ...]
    coverage_complete: bool | None
    page_count: int | None
    errors: tuple[str, ...]
    reason: str | None
    units: tuple[dict[str, Any], ...]


class ProcessedParseSessionPort(SourceChunkSink, Protocol):
    """Parser-owned staging session for a source reader's verified stream."""

    def parse_verified(
        self, receipt: VerifiedVersionReceipt,
    ) -> ProcessedParseOutcome: ...

    def close(self) -> None: ...


class ProcessedDocumentParserPort(Protocol):
    """Public parser interface; it receives verified values, never storage."""

    def requires_verified_content(
        self, descriptor: SourceProcessingDescriptor,
    ) -> bool: ...

    def parse_verified_content(
        self, content: VerifiedContent, descriptor: SourceProcessingDescriptor,
    ) -> ProcessedParseOutcome: ...

    def begin_stream(
        self, descriptor: SourceProcessingDescriptor,
    ) -> ProcessedParseSessionPort: ...


def _format_suffix(descriptor: SourceProcessingDescriptor) -> str:
    hint = descriptor.format_hint
    return f".{hint}" if hint else ""


def _direct_lane_mime(suffix: str, mime_type: str) -> str:
    supported = PROCESSED_DIRECT_FORMATS[suffix]
    main = (mime_type or "").split(";")[0].strip().lower()
    return main if main in supported else sorted(supported)[0]


def _unit_id(
    *, content_sha256: str, parser_name: str, parser_version: str,
    kind: str, locator: str,
) -> str:
    value = {
        "content_sha256": content_sha256,
        "parser_name": parser_name,
        "parser_version": parser_version,
        "kind": kind,
        "locator": locator,
    }
    canonical = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
    )
    return "urn:company-wiki:processed-unit:sha256:" + hashlib.sha256(
        canonical.encode("utf-8")
    ).hexdigest()


def _direct_outcome(
    content: VerifiedContent, descriptor: SourceProcessingDescriptor,
) -> ProcessedParseOutcome:
    ref = descriptor.source_ref
    suffix = _format_suffix(descriptor)
    mime_type = _direct_lane_mime(suffix, ref.mime_type)
    from company_wiki.document_normalization.units import parser_version_for_format

    try:
        document = normalize_verified_document(
            content,
            mime_type=mime_type,
            limits=NormalizationLimits(),
        )
    except UnsupportedFormatError as exc:
        return ProcessedParseOutcome(
            parser_name="unsupported_format", parser_version="1.0.0",
            status="unsupported", quality_flags=("unsupported_format",),
            coverage_complete=None, page_count=None, errors=(),
            reason=str(exc)[:500], units=(),
        )
    except (NormalizationError, ValueError) as exc:
        raise SourceReadError("unavailable", "normalization_failed") from exc

    structure = document.structure
    units: list[dict[str, Any]] = []
    quality_flags: set[str] = set()
    parser_version = parser_version_for_format(suffix.lstrip("."))
    for unit in structure.units:
        locator = unit.metadata.get("source_locator") or unit.coordinates.locator()
        if not isinstance(locator, str) or not locator:
            locator = unit.coordinates.locator()
        units.append({
            "unit_id": unit.unit_id,
            "kind": unit.unit_kind or "text",
            "locator": locator,
            "content": unit.raw_text,
        })
        quality_flags.update(unit.quality_flags)
        parser_version = unit.parser_version
    status = (
        "complete"
        if structure.coverage_complete and not structure.errors else "partial"
    )
    return ProcessedParseOutcome(
        parser_name=DN_PARSER_NAME,
        parser_version=parser_version,
        status=status,
        quality_flags=tuple(sorted(quality_flags)),
        coverage_complete=bool(structure.coverage_complete),
        page_count=structure.page_count,
        errors=tuple(str(item) for item in structure.errors),
        reason=None,
        units=tuple(units),
    )


def _port_parse_source(
    path: Path, manifest, docling_path: Path | None,
) -> NormalizedDocument:
    """Adapt XLSX sheets; delegate all other files to the catalog parser."""
    if path.suffix.lower() == ".xlsx":
        return _xlsx_structured(path, manifest.source_id)
    from .normalizer import normalize_source_file

    try:
        return normalize_source_file(path, manifest, docling_path)
    except ValueError as exc:
        if str(exc) == "empty text output":
            return unsupported_result(path, "empty text output")
        raise


def _xlsx_structured(path: Path, source_id: str) -> NormalizedDocument:
    import openpyxl

    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        results: list[ParserResult] = []
        for sheet_index, sheet in enumerate(workbook.worksheets):
            rows = [list(row) for row in sheet.iter_rows(values_only=True)]
            while rows and not any(value not in (None, "") for value in rows[-1]):
                rows.pop()
            if not rows:
                continue
            raw = "\n".join(
                " | ".join(escape_table_cell(value) for value in row)
                for row in rows
            )
            structured_rows = [
                [None if value is None else str(value) for value in row]
                for row in rows
            ]
            results.append(ParserResult(
                source_id=source_id,
                coordinates=EvidenceCoordinates(table_index=sheet_index),
                raw_text=raw,
                structured_value={"sheet": sheet.title, "rows": structured_rows},
                parser_name="openpyxl",
                parser_version=str(openpyxl.__version__),
                parse_status=ParseStatus.PARSED,
                quality_flags=(),
            ))
    finally:
        workbook.close()
    if not results:
        raise ValueError("XLSX contains no non-empty sheets")
    return NormalizedDocument(
        body="",
        parser_results=tuple(results),
        parser_name="openpyxl",
        parser_version=str(openpyxl.__version__),
        status="completed",
        quality_flags=(),
    )


def _sanitize_temp_path(text: str, data_path: Path) -> str:
    cleaned = text.replace(str(data_path), "<parser_tmp>")
    posix = data_path.as_posix()
    return cleaned.replace(posix, "<parser_tmp>") if posix in cleaned else cleaned


def _isolated_outcome(
    path: Path,
    descriptor: SourceProcessingDescriptor,
) -> ProcessedParseOutcome:
    try:
        normalized = run_parser_isolated(
            path,
            descriptor,
            None,
            timeout_seconds=_PARSER_TIMEOUT_SECONDS,
            heartbeat_interval_seconds=_PARSER_HEARTBEAT_SECONDS,
            result_max_bytes=_PARSER_RESULT_MAX_BYTES,
            temp_dir=path.parent,
            parser=_port_parse_source,
        )
    except UnsupportedDocumentError as exc:
        return _outcome_from_normalized(
            unsupported_result(path, _sanitize_temp_path(str(exc), path)),
            content_sha256=descriptor.source_ref.content_sha256,
        )
    except NormalizationTimeoutError as exc:
        raise SourceReadError("unavailable", "budget_exceeded") from exc
    except NormalizationCancelledError as exc:
        raise SourceReadError("unavailable", "cancelled") from exc
    except ParserProcessError as exc:
        raise SourceReadError("unavailable", "parser_failed") from exc
    return _outcome_from_normalized(
        normalized, content_sha256=descriptor.source_ref.content_sha256,
    )


def _outcome_from_normalized(
    normalized: NormalizedDocument, *, content_sha256: str,
) -> ProcessedParseOutcome:
    status = _STATUS_BY_CATALOG_STATUS.get(normalized.status)
    if status is None:
        raise SourceReadError("unavailable", "parser_status_invalid")
    return ProcessedParseOutcome(
        parser_name=normalized.parser_name,
        parser_version=normalized.parser_version,
        status=status,
        quality_flags=tuple(normalized.quality_flags),
        coverage_complete=None,
        page_count=normalized.page_count,
        errors=(normalized.error,) if normalized.error else (),
        reason=normalized.error if status == "unsupported" else None,
        units=_units_from_results(
            normalized.parser_results, content_sha256=content_sha256,
        ),
    )


def _units_from_results(
    results: tuple[ParserResult, ...], *, content_sha256: str,
) -> tuple[dict[str, Any], ...]:
    units: list[dict[str, Any]] = []
    for result in results:
        coordinates = result.coordinates
        structured = result.structured_value
        if isinstance(structured, Mapping) and "sheet" in structured:
            kind = "sheet"
            content: Any = plain_json_value(structured)
        elif coordinates.table_index is not None:
            kind = "table"
            content = result.raw_text
        else:
            kind = "text"
            content = result.raw_text
        locator = coordinates.locator()
        units.append({
            "unit_id": _unit_id(
                content_sha256=content_sha256,
                parser_name=result.parser_name,
                parser_version=result.parser_version,
                kind=kind,
                locator=locator,
            ),
            "kind": kind,
            "locator": locator,
            "content": content,
        })
    return tuple(units)


class _TempFileParseSession:
    """Stage only provisional chunks; expose a path after receipt commit."""

    def __init__(self, descriptor: SourceProcessingDescriptor):
        self.descriptor = descriptor
        self._temporary = tempfile.TemporaryDirectory(prefix="cwp-parser-")
        suffix = _format_suffix(descriptor)
        self.path = Path(self._temporary.name) / f"source{suffix}"
        self._handle: BinaryIO | None = None
        self._size = 0
        self._receipt: VerifiedVersionReceipt | None = None

    def begin_candidate(self) -> None:
        self.discard_candidate()
        self._handle = self.path.open("wb")
        self._size = 0

    def write_chunk(self, chunk: bytes) -> None:
        if self._handle is None:
            raise SourceChunkSinkError("parser stage has no active candidate")
        if self._handle.write(chunk) != len(chunk):
            raise OSError("parser stage did not accept the complete source chunk")
        self._size += len(chunk)

    def discard_candidate(self) -> None:
        if self._handle is not None:
            self._handle.close()
            self._handle = None
        self.path.unlink(missing_ok=True)
        self._size = 0
        self._receipt = None

    def commit_verified(self, receipt: VerifiedVersionReceipt) -> None:
        if self._handle is None:
            raise SourceChunkSinkError("parser stage has no candidate to commit")
        self._handle.close()
        self._handle = None
        ref = self.descriptor.source_ref
        if (
            receipt.document_id != ref.document_id
            or receipt.source_id != ref.source_id
            or receipt.content_sha256 != ref.content_sha256
            or receipt.byte_size != ref.byte_size
            or self._size != ref.byte_size
        ):
            raise SourceChunkSinkError("verified source receipt does not match staged input")
        self._receipt = receipt

    def parse_verified(self, receipt: VerifiedVersionReceipt) -> ProcessedParseOutcome:
        if self._receipt != receipt or not self.path.is_file():
            raise SourceChunkSinkError("parser stage is not committed for this receipt")
        return _isolated_outcome(self.path, self.descriptor)

    def close(self) -> None:
        failure: Exception | None = None
        try:
            self.discard_candidate()
        except Exception as exc:
            failure = exc
        try:
            self._temporary.cleanup()
        except Exception as exc:
            if failure is None:
                failure = exc
        if failure is not None:
            raise SourceChunkSinkError("parser staging cleanup failed") from failure


class DefaultProcessedDocumentParser:
    """Default format router and parser adapter for the processed-read port."""

    def requires_verified_content(
        self, descriptor: SourceProcessingDescriptor,
    ) -> bool:
        return _format_suffix(descriptor) in PROCESSED_DIRECT_FORMATS

    def parse_verified_content(
        self, content: VerifiedContent, descriptor: SourceProcessingDescriptor,
    ) -> ProcessedParseOutcome:
        return _direct_outcome(content, descriptor)

    def begin_stream(
        self, descriptor: SourceProcessingDescriptor,
    ) -> ProcessedParseSessionPort:
        return _TempFileParseSession(descriptor)


__all__ = [
    "DefaultProcessedDocumentParser",
    "PROCESSED_DIRECT_FORMATS",
    "ProcessedDocumentParserPort",
    "ProcessedParseOutcome",
    "ProcessedParseSessionPort",
]
