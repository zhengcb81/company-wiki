"""Pure consumer contract for an earnings-transcript result `/2` envelope."""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any
from urllib.parse import urlsplit

from .acquisition import DownloadCandidate
from .resolver import SourceRequest


TRANSCRIPT_RESULT_SCHEMA = "earnings-transcript-result/2"
MAX_TOOL_RESULT_BYTES = 25 * 1024 * 1024
MAX_PROVIDER_PAYLOAD_BYTES = 16 * 1024 * 1024
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_UTC_TIMESTAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
_MIME_TYPES = frozenset({"text/html", "application/xhtml+xml", "text/plain"})
_RESULT_FIELDS = frozenset(
    {
        "schema_version",
        "request_id",
        "status",
        "provider",
        "ticker",
        "exchange",
        "fiscal_period",
        "as_of_date",
        "title",
        "source_url",
        "provider_document_id",
        "published_date",
        "extraction_version",
        "provider_payload_sha256",
        "canonical_content_sha256",
        "content_bytes",
        "provider_payload_encoding",
        "provider_payload_base64",
        "provider_payload_mime_type",
        "effective_url",
        "http_status",
        "retrieved_at",
        "adapter_name",
        "adapter_version",
    }
)


class TranscriptToolContractError(ValueError):
    """The provider tool result does not satisfy the frozen `/2` contract."""


@dataclass(frozen=True)
class ValidatedTranscriptPayload:
    original: bytes
    mime_type: str
    retrieved_at: str
    adapter_name: str
    adapter_version: str
    provider_payload_sha256: str
    extraction_version: str
    effective_url: str
    http_status: int
    canonical_content_sha256: str
    content_bytes: int


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise TranscriptToolContractError("duplicate JSON object key")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise TranscriptToolContractError(f"invalid JSON constant: {value}")


def _text(value: Any, name: str, *, max_length: int = 2048) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or len(value) > max_length
    ):
        raise TranscriptToolContractError(f"invalid {name}")
    return value


def _digest(value: Any, name: str) -> str:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise TranscriptToolContractError(f"invalid {name}")
    return value


def _timestamp(value: Any) -> str:
    if not isinstance(value, str) or not _UTC_TIMESTAMP.fullmatch(value):
        raise TranscriptToolContractError("invalid retrieved_at")
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise TranscriptToolContractError("invalid retrieved_at") from exc
    if parsed.strftime("%Y-%m-%dT%H:%M:%SZ") != value:
        raise TranscriptToolContractError("invalid retrieved_at")
    return value


def _raw_text(raw_result: bytes | str) -> str:
    if isinstance(raw_result, bytes):
        if not raw_result or len(raw_result) > MAX_TOOL_RESULT_BYTES:
            raise TranscriptToolContractError("tool result exceeds byte limit")
        try:
            return raw_result.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise TranscriptToolContractError("tool result is not UTF-8") from exc
    if isinstance(raw_result, str):
        if not raw_result or len(raw_result.encode("utf-8")) > MAX_TOOL_RESULT_BYTES:
            raise TranscriptToolContractError("tool result exceeds byte limit")
        return raw_result
    raise TranscriptToolContractError("tool result must be UTF-8 bytes or text")


def _load_payload(raw_result: bytes | str) -> dict[str, Any]:
    try:
        payload = json.loads(
            _raw_text(raw_result),
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except (json.JSONDecodeError, TranscriptToolContractError) as exc:
        raise TranscriptToolContractError("tool result is invalid JSON") from exc
    if not isinstance(payload, dict) or set(payload) != _RESULT_FIELDS:
        raise TranscriptToolContractError("tool result fields differ from schema")
    if payload["schema_version"] != TRANSCRIPT_RESULT_SCHEMA:
        raise TranscriptToolContractError("unsupported transcript result schema")
    if payload["status"] != "fetched":
        raise TranscriptToolContractError("transcript result is not fetched")
    return payload


def _decode_original(payload: dict[str, Any]) -> bytes:
    if payload["provider_payload_encoding"] != "base64":
        raise TranscriptToolContractError("unsupported provider payload encoding")
    encoded = _text(
        payload["provider_payload_base64"],
        "provider_payload_base64",
        max_length=24 * 1024 * 1024,
    )
    try:
        original = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise TranscriptToolContractError("invalid base64 provider payload") from exc
    if not original or len(original) > MAX_PROVIDER_PAYLOAD_BYTES:
        raise TranscriptToolContractError("provider payload is empty or oversized")
    if base64.b64encode(original).decode("ascii") != encoded:
        raise TranscriptToolContractError("provider payload base64 is noncanonical")
    return original


def _validate_result_binding(
    payload: dict[str, Any], request: SourceRequest, candidate: DownloadCandidate
) -> None:
    if payload["request_id"] != request.request_id:
        raise TranscriptToolContractError("result request_id does not match request")
    if _text(payload["provider"], "provider", max_length=64) != candidate.provider:
        raise TranscriptToolContractError("result provider does not match candidate")
    if payload["provider_document_id"] != candidate.provider_document_id:
        raise TranscriptToolContractError(
            "result document identity does not match candidate"
        )
    if payload["source_url"] != candidate.source_url:
        raise TranscriptToolContractError("result source URL does not match candidate")
    if payload["effective_url"] != candidate.source_url:
        raise TranscriptToolContractError(
            "result effective URL differs from selected source"
        )


def _validate_safe_source_url(source_url: str) -> None:
    parsed = urlsplit(source_url)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or bool(parsed.query)
        or bool(parsed.fragment)
    ):
        raise TranscriptToolContractError(
            "candidate source URL is not a safe canonical HTTPS URL"
        )


def _validate_period(
    payload: dict[str, Any], request: SourceRequest, candidate: DownloadCandidate
) -> None:
    if payload["as_of_date"] != request.as_of_date:
        raise TranscriptToolContractError("result as_of_date does not match request")
    if payload["fiscal_period"] != f"{request.fiscal_year}-{request.fiscal_period}":
        raise TranscriptToolContractError("result fiscal period does not match request")
    if payload["published_date"] != candidate.filing_date:
        raise TranscriptToolContractError(
            "result publication date does not match candidate"
        )
    try:
        published = date.fromisoformat(payload["published_date"])
        as_of = date.fromisoformat(request.as_of_date)
    except (TypeError, ValueError) as exc:
        raise TranscriptToolContractError("invalid published_date") from exc
    if published.isoformat() != payload["published_date"] or published > as_of:
        raise TranscriptToolContractError("invalid or future published_date")


def _candidate_identity(candidate: DownloadCandidate) -> dict[str, Any]:
    try:
        identity = json.loads(candidate.adapter_payload_json or "null")
    except json.JSONDecodeError as exc:
        raise TranscriptToolContractError(
            "candidate security identity is invalid"
        ) from exc
    if not isinstance(identity, dict):
        raise TranscriptToolContractError("candidate security identity is missing")
    return identity


def _ticker_key(value: str) -> str:
    return value.upper().replace(".", "-")


def _validate_security(
    payload: dict[str, Any], request: SourceRequest, candidate: DownloadCandidate
) -> None:
    identity = _candidate_identity(candidate)
    expected_exchange = identity.get("exchange")
    result_ticker = _text(payload["ticker"], "ticker", max_length=32)
    result_exchange = _text(payload["exchange"], "exchange", max_length=32)
    matches = (
        isinstance(request.security_id, str)
        and _ticker_key(result_ticker) == _ticker_key(request.security_id)
        and isinstance(expected_exchange, str)
        and result_exchange.casefold() == expected_exchange.casefold()
        and result_exchange.casefold() in {"nyse", "nasdaq"}
        and identity.get("market") == request.market
        and identity.get("security_id") == request.security_id
    )
    if not matches:
        raise TranscriptToolContractError(
            "result ticker/exchange does not match selected security"
        )


def _validate_payload_metadata(
    payload: dict[str, Any], original: bytes, *, max_bytes: int
) -> tuple[str, str, str]:
    _text(payload["title"], "title", max_length=512)
    extraction = _text(
        payload["extraction_version"], "extraction_version", max_length=128
    )
    payload_sha = _digest(
        payload["provider_payload_sha256"], "provider_payload_sha256"
    )
    _digest(payload["canonical_content_sha256"], "canonical_content_sha256")
    if hashlib.sha256(original).hexdigest() != payload_sha:
        raise TranscriptToolContractError("provider payload SHA-256 mismatch")
    if type(payload["content_bytes"]) is not int or not (
        0 < payload["content_bytes"] <= MAX_TOOL_RESULT_BYTES
    ):
        raise TranscriptToolContractError("invalid content_bytes")
    if type(payload["http_status"]) is not int or payload["http_status"] != 200:
        raise TranscriptToolContractError("provider HTTP status is not successful")
    mime_type = _text(
        payload["provider_payload_mime_type"], "provider payload MIME type"
    ).lower()
    if mime_type not in _MIME_TYPES:
        raise TranscriptToolContractError("unsupported transcript MIME type")
    if type(max_bytes) is not int or not 0 < max_bytes <= MAX_PROVIDER_PAYLOAD_BYTES:
        raise TranscriptToolContractError("invalid provider payload byte cap")
    if len(original) > max_bytes:
        raise TranscriptToolContractError("provider payload exceeds byte cap")
    return mime_type, extraction, payload_sha


def parse_transcript_tool_result(
    raw_result: bytes | str,
    *,
    request: SourceRequest,
    candidate: DownloadCandidate,
    max_bytes: int = MAX_PROVIDER_PAYLOAD_BYTES,
) -> ValidatedTranscriptPayload:
    payload = _load_payload(raw_result)
    original = _decode_original(payload)
    _validate_result_binding(payload, request, candidate)
    _validate_safe_source_url(candidate.source_url)
    _validate_period(payload, request, candidate)
    _validate_security(payload, request, candidate)
    mime_type, extraction, payload_sha = _validate_payload_metadata(
        payload, original, max_bytes=max_bytes
    )
    return ValidatedTranscriptPayload(
        original=original,
        mime_type=mime_type,
        retrieved_at=_timestamp(payload["retrieved_at"]),
        adapter_name=_text(payload["adapter_name"], "adapter_name", max_length=128),
        adapter_version=_text(
            payload["adapter_version"], "adapter_version", max_length=64
        ),
        provider_payload_sha256=payload_sha,
        extraction_version=extraction,
        effective_url=payload["effective_url"],
        http_status=payload["http_status"],
        canonical_content_sha256=payload["canonical_content_sha256"],
        content_bytes=payload["content_bytes"],
    )
