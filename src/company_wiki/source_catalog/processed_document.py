"""Pathless processed-document reading port: ``company-wiki-processed-document/1``.

D5 (``du11-source-closure-2026-10-18``) frozen consumer contract.  A consumer
names one exact source version by its SourceRef v2 identity — never a path —
and receives the owner's normalized document projection: ordered units with
stable ids, existing locators, the parser identity that produced them, an
honest completeness status and parse-quality diagnostics.

company-wiki stays the single owner of file lookup, verified open, parsing and
parser state. This endpoint composes the public ``SourceVersionPort`` with the
parser-owner interface; it never reaches into catalog storage, manifest JSON,
or physical source locations. Direct normalizer formats consume the verified
content object. Other formats stream to a parser-owned temporary stage, which
is visible only after the source reader commits its verified receipt.

The response never contains a physical path, storage root, SQLite detail or
neighbour-repo location.  Legacy ``SourceManifest.to_dict()`` (which carries
``original_path``) is never emitted; the ``manifest`` field is the same
pathless 23-field projection the SourceExport v2 bundle publishes.
"""

from __future__ import annotations

import base64
import binascii
import json
import logging
from typing import Any

from company_wiki.source_contract import (
    SourceChunkSinkError,
    SourceReadBudgetPort,
    SourceReadError,
    SourceRef,
    SourceVersionPort,
)
from .processed_document_parser import (
    DefaultProcessedDocumentParser,
    ProcessedDocumentParserPort,
)

PROCESSED_DOCUMENT_SCHEMA_VERSION = "company-wiki-processed-document/1"
_PROCESSED_UNIT_URN_PREFIX = "urn:company-wiki:processed-unit:sha256:"
_LOGGER = logging.getLogger(__name__)

_REQUEST_REQUIRED_FIELDS = frozenset({"schema_version", "source_ref"})
_REQUEST_OPTIONAL_FIELDS = frozenset({"options"})
_OPTION_FIELDS = frozenset({"max_units", "continuation"})


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


def read_processed_document(
    reader: SourceVersionPort,
    request: Any,
    *,
    parser: ProcessedDocumentParserPort | None = None,
    budget: SourceReadBudgetPort | None = None,
) -> dict[str, Any]:
    """Serve one ``company-wiki-processed-document/1`` response for a request."""
    _validate_request(request)
    ref = SourceRef.from_dict(request["source_ref"])
    descriptor = reader.describe_processing_version(ref)
    manifest = reader.describe_version(ref)
    parser = DefaultProcessedDocumentParser() if parser is None else parser
    if parser.requires_verified_content(descriptor):
        content = reader.open_version(
            ref, purpose="source_export", budget=budget,
        )
        outcome = parser.parse_verified_content(content, descriptor)
    else:
        session = parser.begin_stream(descriptor)
        primary_error: BaseException | None = None
        try:
            receipt = reader.stream_version(
                ref,
                sink=session,
                purpose="source_export",
                budget=budget,
            )
            outcome = session.parse_verified(receipt)
        except SourceReadError as exc:
            primary_error = exc
            raise
        except SourceChunkSinkError as exc:
            mapped = SourceReadError(
                "unavailable", "processed_document_failed",
            )
            primary_error = mapped
            raise mapped from exc
        except Exception as exc:
            mapped = SourceReadError("unavailable", "processed_document_failed")
            primary_error = mapped
            raise mapped from exc
        except BaseException as exc:
            primary_error = exc
            raise
        finally:
            try:
                session.close()
            except Exception as exc:
                if primary_error is None:
                    raise SourceReadError(
                        "unavailable", "processed_document_cleanup_failed",
                    ) from exc
                _LOGGER.warning(
                    "Parser session cleanup also failed (%s) while preserving the primary error",
                    type(exc).__name__,
                )

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
    # Frozen contract: a non-final page never claims complete — a paginated
    # response that hides later units would be a fake-complete.
    status = "partial" if continuation is not None else outcome.status
    return {
        "schema_version": PROCESSED_DOCUMENT_SCHEMA_VERSION,
        "source_ref": ref.to_dict(),
        "manifest": manifest,
        "parser": {
            "name": outcome.parser_name,
            "version": outcome.parser_version,
            "profile": None,
        },
        "status": status,
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
