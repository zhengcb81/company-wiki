"""Pathless processed-document reading port: ``company-wiki-processed-document/1``.

D5 (``du11-source-closure-2026-10-18``) frozen consumer contract.  A consumer
names one exact source version by its SourceRef v2 identity — never a path —
and receives the owner's normalized document projection: ordered units with
stable ids, existing locators, the parser identity that produced them, an
honest completeness status and parse-quality diagnostics.

company-wiki stays the single owner of file lookup, verified open, parsing and
parser state: the port reads bytes through :class:`SourceVersionReader`
(same verified-open chain as every other public reader, purpose
``source_export``) and reuses the catalog's parse composition — the pure
``document_normalization`` lane for DOCX/HTML/PPTX and the isolated parser
process for PDF/XLSX/text and everything else the catalog already parses.
Nothing here re-implements a parser, adds a second cache, or invents budgets:
parser isolation, deadlines and result caps come from the existing owner
machinery (``normalizer._run_parser_isolated`` defaults).

The response never contains a physical path, storage root, SQLite detail or
neighbour-repo location.  Legacy ``SourceManifest.to_dict()`` (which carries
``original_path``) is never emitted; the ``manifest`` field is the same
pathless 22-field projection the SourceExport v2 bundle publishes.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from company_wiki.automation.narrative_contracts import SourceRefValue
from company_wiki.document_normalization import (
    PARSER_NAME as DN_PARSER_NAME,
    PARSER_VERSION as DN_PARSER_VERSION,
    NormalizationError,
    NormalizationLimits,
    UnsupportedFormatError,
    normalize_document,
)
from company_wiki.canonical_ingest import ParserResult
from company_wiki.source_contract import EvidenceCoordinates, ParseStatus
from company_wiki.source_contract.evidence_span import _plain_json
from company_wiki.source_contract.source_manifest import SourceManifest
from company_wiki.source_contract.source_version import SourceReadError, SourceRef

from .normalizer import (
    NormalizationCancelledError,
    NormalizationTimeoutError,
    ParserProcessError,
    UnsupportedDocumentError,
    _Normalized,
    _escape_cell,
    _normalize_source,
    _run_parser_isolated,
    _unsupported,
)
from .source_reader import SourceVersionReader

PROCESSED_DOCUMENT_SCHEMA_VERSION = "company-wiki-processed-document/1"
_PROCESSED_UNIT_URN_PREFIX = "urn:company-wiki:processed-unit:sha256:"

_REQUEST_REQUIRED_FIELDS = frozenset({"schema_version", "source_ref"})
_REQUEST_OPTIONAL_FIELDS = frozenset({"options"})
_OPTION_FIELDS = frozenset({"max_units", "continuation"})

#: Formats parsed in-process through the pure normalizer (R6-FORMAT owner).
#: The suffix decides the lane; the source's own mime type is used when it is
#: one this format actually supports, so a variant mime (xhtml, pptx
#: slideshow) is parsed as itself rather than re-labelled.
_DIRECT_LANE_SUFFIXES = {
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

#: Parser runtime budgets: the catalog owner's own defaults (the same values
#: ``backfill_text_fingerprints`` uses), not a new budget surface.
_PARSER_TIMEOUT_SECONDS = 3600.0
_PARSER_HEARTBEAT_SECONDS = 15.0
_PARSER_RESULT_MAX_BYTES = 268_435_456

_STATUS_BY_CATALOG_STATUS = {
    "completed": "complete",
    "partial": "partial",
    "unsupported": "unsupported",
}


@dataclass(frozen=True)
class _Outcome:
    """Parsed result mapped into the frozen envelope vocabulary."""

    parser_name: str
    parser_version: str
    status: str
    quality_flags: tuple[str, ...]
    coverage_complete: bool | None
    page_count: int | None
    errors: tuple[str, ...]
    reason: str | None
    units: tuple[dict[str, Any], ...]


def _validate_request(request: Any) -> None:
    if not isinstance(request, dict):
        raise ValueError("processed document request must be an object")
    fields = set(request)
    if not _REQUEST_REQUIRED_FIELDS <= fields <= (
        _REQUEST_REQUIRED_FIELDS | _REQUEST_OPTIONAL_FIELDS
    ):
        raise ValueError("request fields are not exact")
    if request["schema_version"] != PROCESSED_DOCUMENT_SCHEMA_VERSION:
        raise SourceReadError("blocked", "unsupported_request_version")
    options = request.get("options")
    if options is None:
        return
    if not isinstance(options, dict) or not set(options) <= _OPTION_FIELDS:
        raise ValueError("request options fields are not exact")
    max_units = options.get("max_units")
    if max_units is not None and (
        isinstance(max_units, bool)
        or not isinstance(max_units, int)
        or max_units < 1
    ):
        raise ValueError("options.max_units must be a positive integer")
    continuation = options.get("continuation")
    if continuation is not None and not isinstance(continuation, str):
        raise ValueError("options.continuation must be text")


def _encode_cursor(*, after_index: int, after_unit_id: str, content_sha256: str) -> str:
    payload = {
        "v": 1,
        "after_index": after_index,
        "after_unit_id": after_unit_id,
        "content_sha256": content_sha256,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii")


def _decode_cursor(token: str, *, content_sha256: str) -> tuple[int, str]:
    try:
        raw = base64.urlsafe_b64decode(token.encode("ascii"))
        payload = json.loads(raw.decode("utf-8"))
    except (binascii.Error, UnicodeError, ValueError):
        raise SourceReadError("blocked", "invalid_continuation") from None
    expected = {"v", "after_index", "after_unit_id", "content_sha256"}
    if (
        not isinstance(payload, dict)
        or set(payload) != expected
        or payload["v"] != 1
        or payload["content_sha256"] != content_sha256
        or isinstance(payload["after_index"], bool)
        or not isinstance(payload["after_index"], int)
        or payload["after_index"] < 0
        or not isinstance(payload["after_unit_id"], str)
        or not payload["after_unit_id"]
    ):
        raise SourceReadError("blocked", "invalid_continuation")
    return payload["after_index"], payload["after_unit_id"]


def _processed_unit_id(
    *, content_sha256: str, parser_name: str, parser_version: str,
    kind: str, locator: str,
) -> str:
    payload = {
        "content_sha256": content_sha256,
        "parser_name": parser_name,
        "parser_version": parser_version,
        "kind": kind,
        "locator": locator,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=True)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return _PROCESSED_UNIT_URN_PREFIX + digest


def _location_manifest(reader: SourceVersionReader, ref: SourceRef) -> SourceManifest:
    """The indexed location's own legacy manifest, for the parser child only.

    The child process needs the owner's SourceManifest to attribute parse
    results to the exact source identity.  This object (which carries
    ``original_path``) never travels into the response.
    """
    try:
        rows = reader.catalog.reader.exact_source_locations(
            ref.document_id, ref.source_id
        )
    except Exception as exc:  # catalog reader boundary (sqlite / unavailable)
        raise SourceReadError("unavailable", "catalog_unavailable") from exc
    for row in rows:
        location = dict(row)
        if str(location.get("location_status") or "active") != "active":
            continue
        raw = location.get("manifest_json")
        if not raw:
            continue
        try:
            payload = json.loads(raw) if isinstance(raw, str) else raw
            manifest = SourceManifest.from_dict(payload)
        except Exception:
            continue
        if (
            manifest.source_id == ref.source_id
            and manifest.content_sha256 == ref.content_sha256
        ):
            return manifest
    raise SourceReadError("unavailable", "source_manifest_unavailable")


def _direct_lane_mime(suffix: str, mime_type: str) -> str:
    """The mime type the pure normalizer should parse this source as.

    A variant mime the format genuinely supports (xhtml, pptx slideshow) is
    kept as itself; anything else falls back to the format's canonical type
    so a mislabelled source still reaches its own parser.
    """
    supported = _DIRECT_LANE_SUFFIXES[suffix]
    main = (mime_type or "").split(";")[0].strip().lower()
    if main in supported:
        return main
    return sorted(supported)[0]


def _parse_direct_lane(data: bytes, *, ref: SourceRef, mime_type: str) -> _Outcome:
    """Parse DOCX/HTML/PPTX with the pure document_normalization owner."""
    try:
        document = normalize_document(
            data,
            source_id=ref.source_id,
            source_sha256=ref.content_sha256,
            mime_type=mime_type,
            limits=NormalizationLimits(),
        )
    except UnsupportedFormatError as exc:
        return _Outcome(
            parser_name="unsupported_format",
            parser_version="1.0.0",
            status="unsupported",
            quality_flags=("unsupported_format",),
            coverage_complete=None,
            page_count=None,
            errors=(),
            reason=str(exc)[:500],
            units=(),
        )
    except (NormalizationError, ValueError) as exc:
        raise SourceReadError("unavailable", "normalization_failed") from exc
    structure = document.structure
    units: list[dict[str, Any]] = []
    quality_flags: set[str] = set()
    parser_version = DN_PARSER_VERSION
    for unit in structure.units:
        locator = unit.metadata.get("source_locator") or unit.coordinates.locator()
        if not isinstance(locator, str) or not locator:
            locator = unit.coordinates.locator()
        kind = unit.unit_kind if unit.unit_kind else "text"
        units.append(
            {
                "unit_id": unit.unit_id,
                "kind": kind,
                "locator": locator,
                "content": unit.raw_text,
            }
        )
        quality_flags.update(unit.quality_flags)
        parser_version = unit.parser_version
    status = (
        "complete"
        if structure.coverage_complete and not structure.errors
        else "partial"
    )
    return _Outcome(
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
    path: Path, manifest: SourceManifest, docling_path: Path | None
) -> _Normalized:
    """Isolated-child parser: the catalog dispatch plus the D5 sheet adapter.

    The catalog parser emits one unit per workbook sheet as pipe-joined text;
    the frozen D5 contract requires structured row/cell boundaries, so XLSX is
    read here into explicit rows while every other format keeps the catalog's
    own dispatch unchanged.
    """
    suffix = path.suffix.lower()
    if suffix == ".xlsx":
        return _xlsx_structured(path, manifest.source_id)
    try:
        return _normalize_source(path, manifest, docling_path)
    except ValueError as exc:
        if str(exc) == "empty text output":
            # An empty text source is honestly unsupported, not a fake parse.
            return _unsupported(path, "empty text output")
        raise


def _xlsx_structured(path: Path, source_id: str) -> _Normalized:
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
                " | ".join(_escape_cell(value) for value in row) for row in rows
            )
            structured_rows = [
                [None if value is None else str(value) for value in row]
                for row in rows
            ]
            results.append(
                ParserResult(
                    source_id=source_id,
                    coordinates=EvidenceCoordinates(table_index=sheet_index),
                    raw_text=raw,
                    structured_value={"sheet": sheet.title, "rows": structured_rows},
                    parser_name="openpyxl",
                    parser_version=str(openpyxl.__version__),
                    parse_status=ParseStatus.PARSED,
                    quality_flags=(),
                )
            )
    finally:
        workbook.close()
    if not results:
        raise ValueError("XLSX contains no non-empty sheets")
    return _Normalized(
        body="",
        parser_results=tuple(results),
        parser_name="openpyxl",
        parser_version=str(openpyxl.__version__),
        status="completed",
        quality_flags=(),
    )


def _parse_isolated_lane(
    config: Any, *, content: Any, manifest: SourceManifest
) -> _Outcome:
    """Parse every non-pure format through the catalog's isolated parser."""
    suffix = Path(manifest.original_path).suffix.lower()
    parser_tmp = config.catalog_dir / "parser_tmp"
    data_path = parser_tmp / f"processed-{manifest.content_sha256[:32]}{suffix or '.bin'}"
    data_path.parent.mkdir(parents=True, exist_ok=True)
    data_path.write_bytes(content.data)
    try:
        try:
            normalized = _run_parser_isolated(
                data_path,
                manifest,
                None,
                timeout_seconds=_PARSER_TIMEOUT_SECONDS,
                heartbeat_interval_seconds=_PARSER_HEARTBEAT_SECONDS,
                result_max_bytes=_PARSER_RESULT_MAX_BYTES,
                temp_dir=parser_tmp,
                parser=_port_parse_source,
            )
        except UnsupportedDocumentError as exc:
            # The parser proved these bytes unparseable for their format: say
            # so honestly instead of inventing a parse or a fake failure.
            return _outcome_from_normalized(
                _unsupported(data_path, str(exc)),
                content_sha256=manifest.content_sha256,
            )
        except NormalizationTimeoutError as exc:
            raise SourceReadError("unavailable", "budget_exceeded") from exc
        except NormalizationCancelledError as exc:
            raise SourceReadError("unavailable", "cancelled") from exc
        except ParserProcessError as exc:
            raise SourceReadError("unavailable", "parser_failed") from exc
    finally:
        data_path.unlink(missing_ok=True)
    return _outcome_from_normalized(
        normalized, content_sha256=manifest.content_sha256,
    )


def _outcome_from_normalized(
    normalized: _Normalized, *, content_sha256: str,
) -> _Outcome:
    status = _STATUS_BY_CATALOG_STATUS.get(normalized.status)
    if status is None:
        raise SourceReadError("unavailable", "parser_status_invalid")
    return _Outcome(
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
        coordinates: EvidenceCoordinates = result.coordinates
        structured = result.structured_value
        if isinstance(structured, Mapping) and "sheet" in structured:
            kind = "sheet"
            content: Any = _plain_json(structured)
        elif coordinates.table_index is not None:
            kind = "table"
            content = result.raw_text
        else:
            kind = "text"
            content = result.raw_text
        locator = coordinates.locator()
        units.append(
            {
                "unit_id": _processed_unit_id(
                    content_sha256=content_sha256,
                    parser_name=result.parser_name,
                    parser_version=result.parser_version,
                    kind=kind,
                    locator=locator,
                ),
                "kind": kind,
                "locator": locator,
                "content": content,
            }
        )
    return tuple(units)


def read_processed_document(
    reader: SourceVersionReader, request: Any
) -> dict[str, Any]:
    """Serve one ``company-wiki-processed-document/1`` response for a request."""
    _validate_request(request)
    ref_value = SourceRefValue.from_dict(request["source_ref"])
    ref = SourceRef(
        schema_version=ref_value.schema_version,
        document_id=ref_value.document_id,
        source_id=ref_value.source_id,
        content_sha256=ref_value.content_sha256,
        byte_size=ref_value.byte_size,
        mime_type=ref_value.mime_type,
    )
    content, manifest = reader.open_described_version(ref, purpose="source_export")
    if content.data is None:  # pragma: no cover - retain_bytes=True guarantees bytes
        raise SourceReadError("unavailable", "verification_invariant_broken")
    location_manifest = _location_manifest(reader, ref)
    suffix = Path(location_manifest.original_path).suffix.lower()
    if suffix in _DIRECT_LANE_SUFFIXES:
        outcome = _parse_direct_lane(
            content.data,
            ref=ref,
            mime_type=_direct_lane_mime(suffix, ref.mime_type),
        )
    else:
        try:
            outcome = _parse_isolated_lane(
                reader.catalog.config, content=content, manifest=location_manifest,
            )
        except SourceReadError:
            raise
        except Exception as exc:
            raise SourceReadError("unavailable", "processed_document_failed") from exc

    units = list(outcome.units)
    start = 0
    options = request.get("options") or {}
    max_units = options.get("max_units")
    continuation_token = options.get("continuation")
    if continuation_token is not None:
        start, after_unit_id = _decode_cursor(
            continuation_token, content_sha256=ref.content_sha256
        )
        if start > len(units) or (
            start > 0 and units[start - 1]["unit_id"] != after_unit_id
        ):
            raise SourceReadError("blocked", "invalid_continuation")
    if max_units is not None:
        page = units[start : start + max_units]
    else:
        page = units[start:]
    continuation: dict[str, Any] | None = None
    if max_units is not None and start + len(page) < len(units):
        continuation = {
            "cursor": _encode_cursor(
                after_index=start + len(page),
                after_unit_id=page[-1]["unit_id"],
                content_sha256=ref.content_sha256,
            ),
            "has_more": True,
        }
    return {
        "schema_version": PROCESSED_DOCUMENT_SCHEMA_VERSION,
        "source_ref": ref_value.to_dict(),
        "manifest": manifest,
        "parser": {
            "name": outcome.parser_name,
            "version": outcome.parser_version,
            "profile": None,
        },
        "status": outcome.status,
        "units": page,
        "continuation": continuation,
        "quality": {
            "quality_flags": list(outcome.quality_flags),
            "coverage_complete": outcome.coverage_complete,
            "page_count": outcome.page_count,
            "errors": list(outcome.errors),
            "reason": outcome.reason,
        },
    }


__all__ = ["PROCESSED_DOCUMENT_SCHEMA_VERSION", "read_processed_document"]
