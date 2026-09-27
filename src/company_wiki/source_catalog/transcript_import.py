"""Validate and canonically import an authorized transcript-tool result.

The caller must run ``authorize_transcript_fetch`` before invoking the
provider. This importer binds the later result to that admission, rechecks the
current rights policy and exact bytes, then delegates immutable raw storage to
``CanonicalSourceWriter``. It never translates or persists derived text.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import date, datetime
import hashlib
import json
from pathlib import Path
import re
import tempfile
from typing import Any
from urllib.parse import urlsplit

from .acquisition import DownloadCandidate, DownloadReceipt
from .authorization import DownloadAuthorization
from .canonical_writer import CanonicalImportResult, CanonicalSourceWriter
from .provider_use_policy import (
    ProviderUsePolicy,
    TranscriptFetchAdmission,
    validate_transcript_fetch_result,
)
from .resolver import SourceRequest
from .transcript_material import TranscriptMaterial, extract_transcript_material


TRANSCRIPT_RESULT_SCHEMA = "earnings-transcript-result/2"
MAX_TOOL_RESULT_BYTES = 25 * 1024 * 1024
MAX_PROVIDER_PAYLOAD_BYTES = 16 * 1024 * 1024
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_UTC_TIMESTAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
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


class TranscriptImportError(ValueError):
    """A tool result is invalid, unapproved, or cannot be safely imported."""


@dataclass(frozen=True)
class TranscriptImportResult:
    canonical_import: CanonicalImportResult
    material: TranscriptMaterial
    rights_policy_sha256: str
    download_authorization_hash: str
    provider_payload_sha256: str
    provider_extraction_version: str


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise TranscriptImportError("duplicate JSON object key")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise TranscriptImportError(f"invalid JSON constant: {value}")


def _text(value: Any, name: str, *, max_length: int = 2048) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or len(value) > max_length
    ):
        raise TranscriptImportError(f"invalid {name}")
    return value


def _digest(value: Any, name: str) -> str:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise TranscriptImportError(f"invalid {name}")
    return value


def _timestamp(value: Any) -> str:
    if not isinstance(value, str) or not _UTC_TIMESTAMP.fullmatch(value):
        raise TranscriptImportError("invalid retrieved_at")
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise TranscriptImportError("invalid retrieved_at") from exc
    if parsed.strftime("%Y-%m-%dT%H:%M:%SZ") != value:
        raise TranscriptImportError("invalid retrieved_at")
    return value


def _decode_result(raw_result: bytes | str) -> tuple[dict[str, Any], bytes]:
    if isinstance(raw_result, bytes):
        if not raw_result or len(raw_result) > MAX_TOOL_RESULT_BYTES:
            raise TranscriptImportError("tool result exceeds byte limit")
        try:
            raw_text = raw_result.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise TranscriptImportError("tool result is not UTF-8") from exc
    elif isinstance(raw_result, str):
        if not raw_result or len(raw_result.encode("utf-8")) > MAX_TOOL_RESULT_BYTES:
            raise TranscriptImportError("tool result exceeds byte limit")
        raw_text = raw_result
    else:
        raise TranscriptImportError("tool result must be UTF-8 bytes or text")

    try:
        payload = json.loads(
            raw_text,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except (json.JSONDecodeError, TranscriptImportError) as exc:
        raise TranscriptImportError("tool result is invalid JSON") from exc
    if not isinstance(payload, dict) or set(payload) != _RESULT_FIELDS:
        raise TranscriptImportError("tool result fields differ from schema")
    if payload["schema_version"] != TRANSCRIPT_RESULT_SCHEMA:
        raise TranscriptImportError("unsupported transcript result schema")
    if payload["status"] != "fetched":
        raise TranscriptImportError("transcript result is not fetched")
    if payload["provider_payload_encoding"] != "base64":
        raise TranscriptImportError("unsupported provider payload encoding")
    encoded = _text(
        payload["provider_payload_base64"], "provider_payload_base64",
        max_length=24 * 1024 * 1024,
    )
    try:
        original = base64.b64decode(encoded, validate=True)
    except (ValueError, base64.binascii.Error) as exc:
        raise TranscriptImportError("invalid base64 provider payload") from exc
    if (
        not original
        or len(original) > MAX_PROVIDER_PAYLOAD_BYTES
        or base64.b64encode(original).decode("ascii") != encoded
    ):
        raise TranscriptImportError("provider payload is empty, oversized, or noncanonical")
    return payload, original


def _ticker_key(value: str) -> str:
    return value.upper().replace(".", "-")


def _validate_result_identity(
    payload: dict[str, Any],
    original: bytes,
    *,
    request: SourceRequest,
    candidate: DownloadCandidate,
    authorization: DownloadAuthorization,
) -> tuple[str, str]:
    if payload["request_id"] != request.request_id:
        raise TranscriptImportError("result request_id does not match request")
    if _text(payload["provider"], "provider", max_length=64) != candidate.provider:
        raise TranscriptImportError("result provider does not match candidate")
    if payload["provider_document_id"] != candidate.provider_document_id:
        raise TranscriptImportError("result document identity does not match candidate")
    if payload["source_url"] != candidate.source_url:
        raise TranscriptImportError("result source URL does not match candidate")
    if payload["effective_url"] != candidate.source_url:
        raise TranscriptImportError("result effective URL differs from selected source")
    parsed_url = urlsplit(candidate.source_url)
    if (
        parsed_url.scheme != "https"
        or not parsed_url.hostname
        or parsed_url.username is not None
        or parsed_url.password is not None
        or parsed_url.query
        or parsed_url.fragment
    ):
        raise TranscriptImportError("candidate source URL is not a safe canonical HTTPS URL")

    if payload["as_of_date"] != request.as_of_date:
        raise TranscriptImportError("result as_of_date does not match request")
    expected_period = f"{request.fiscal_year}-{request.fiscal_period}"
    if payload["fiscal_period"] != expected_period:
        raise TranscriptImportError("result fiscal period does not match request")
    if payload["published_date"] != candidate.filing_date:
        raise TranscriptImportError("result publication date does not match candidate")
    try:
        published = date.fromisoformat(payload["published_date"])
    except (TypeError, ValueError) as exc:
        raise TranscriptImportError("invalid published_date") from exc
    if published.isoformat() != payload["published_date"] or published > date.fromisoformat(request.as_of_date):
        raise TranscriptImportError("invalid or future published_date")

    identity: Any
    try:
        identity = json.loads(candidate.adapter_payload_json or "null")
    except json.JSONDecodeError as exc:
        raise TranscriptImportError("candidate security identity is invalid") from exc
    if not isinstance(identity, dict):
        raise TranscriptImportError("candidate security identity is missing")
    expected_ticker = request.security_id
    expected_exchange = identity.get("exchange")
    result_ticker = _text(payload["ticker"], "ticker", max_length=32)
    result_exchange = _text(payload["exchange"], "exchange", max_length=32)
    if (
        not isinstance(expected_ticker, str)
        or _ticker_key(result_ticker) != _ticker_key(expected_ticker)
        or not isinstance(expected_exchange, str)
        or result_exchange.casefold() != expected_exchange.casefold()
        or result_exchange.casefold() not in {"nyse", "nasdaq"}
        or identity.get("market") != request.market
        or identity.get("security_id") != request.security_id
    ):
        raise TranscriptImportError("result ticker/exchange does not match selected security")

    _text(payload["title"], "title", max_length=512)
    _text(payload["extraction_version"], "extraction_version", max_length=128)
    _digest(payload["provider_payload_sha256"], "provider_payload_sha256")
    _digest(payload["canonical_content_sha256"], "canonical_content_sha256")
    if hashlib.sha256(original).hexdigest() != payload["provider_payload_sha256"]:
        raise TranscriptImportError("provider payload SHA-256 mismatch")
    if (
        type(payload["content_bytes"]) is not int
        or not 0 < payload["content_bytes"] <= MAX_TOOL_RESULT_BYTES
    ):
        raise TranscriptImportError("invalid content_bytes")
    if type(payload["http_status"]) is not int or payload["http_status"] != 200:
        raise TranscriptImportError("provider HTTP status is not successful")
    mime_type = _text(payload["provider_payload_mime_type"], "provider payload MIME type").lower()
    if mime_type not in {"text/html", "application/xhtml+xml", "text/plain"}:
        raise TranscriptImportError("unsupported transcript MIME type")
    _timestamp(payload["retrieved_at"])
    adapter_name = _text(payload["adapter_name"], "adapter_name", max_length=128)
    adapter_version = _text(payload["adapter_version"], "adapter_version", max_length=64)
    if authorization.max_bytes < len(original):
        raise TranscriptImportError("provider payload exceeds authorized byte cap")
    return mime_type, adapter_name + "\0" + adapter_version


def import_transcript_tool_result(
    raw_result: bytes | str,
    *,
    request: SourceRequest,
    candidate: DownloadCandidate,
    authorization: DownloadAuthorization,
    preflight_admission: TranscriptFetchAdmission,
    plan_hash: str,
    runtime_policy_hash: str,
    current_rights_policy: ProviderUsePolicy,
    writer: CanonicalSourceWriter,
    now: str,
) -> TranscriptImportResult:
    """Post-fetch validate, stage and import one previously authorized result.

    ``preflight_admission`` must be created before the provider fetch with
    ``authorize_transcript_fetch``. The result cannot be imported if its
    request/candidate/auth identity or policy fingerprint differs.
    """
    if (
        not isinstance(request, SourceRequest)
        or not isinstance(candidate, DownloadCandidate)
        or not isinstance(authorization, DownloadAuthorization)
        or not isinstance(writer, CanonicalSourceWriter)
    ):
        raise TranscriptImportError("request, candidate, authorization and writer are required")
    if (
        type(authorization.max_bytes) is not int
        or authorization.max_bytes <= 0
        or authorization.request_id != request.request_id
    ):
        raise TranscriptImportError("download authorization does not bind this request")
    if not isinstance(preflight_admission, TranscriptFetchAdmission):
        raise TranscriptImportError("missing pre-fetch authorization evidence")
    if (
        not preflight_admission.allowed
        or preflight_admission.request_id != request.request_id
        or preflight_admission.candidate_id != candidate.candidate_id
        or preflight_admission.download_authorization_hash != authorization.receipt_hash
        or not preflight_admission.rights_policy_sha256
    ):
        raise TranscriptImportError("pre-fetch authorization does not bind this candidate")
    if not isinstance(current_rights_policy, ProviderUsePolicy):
        raise TranscriptImportError("current rights policy is unavailable")
    if current_rights_policy.policy_sha256 != preflight_admission.rights_policy_sha256:
        raise TranscriptImportError("provider-use policy changed during fetch")

    payload, original = _decode_result(raw_result)
    mime_type, adapter_info = _validate_result_identity(
        payload,
        original,
        request=request,
        candidate=candidate,
        authorization=authorization,
    )
    adapter_name, adapter_version = adapter_info.split("\0", maxsplit=1)
    retrieved_at = _timestamp(payload["retrieved_at"])
    root = writer.staging_root
    root.mkdir(parents=True, exist_ok=True)
    if not root.is_dir() or root.is_symlink():
        raise TranscriptImportError("allocated staging root is unsafe")
    suffix = ".html" if mime_type in {"text/html", "application/xhtml+xml"} else ".txt"
    fd, path_text = tempfile.mkstemp(prefix="transcript-", suffix=suffix, dir=root)
    staged = Path(path_text)
    try:
        with open(fd, "wb", closefd=True) as stream:
            stream.write(original)
            stream.flush()
        receipt = DownloadReceipt(
            candidate_id=candidate.candidate_id,
            provider=candidate.provider,
            provider_document_id=candidate.provider_document_id,
            source_url=candidate.source_url,
            staged_path=str(staged),
            content_sha256=payload["provider_payload_sha256"],
            byte_size=len(original),
            mime_type=mime_type,
            retrieved_at=retrieved_at,
            http_status=payload["http_status"],
            adapter_name=adapter_name,
            adapter_version=adapter_version,
            etag=candidate.etag,
            last_modified=candidate.last_modified,
        )
        validation = validate_transcript_fetch_result(
            request=request,
            candidate=candidate,
            receipt=receipt,
            authorization=authorization,
            plan_hash=plan_hash,
            runtime_policy_hash=runtime_policy_hash,
            pinned_rights_policy_sha256=preflight_admission.rights_policy_sha256,
            current_rights_policy=current_rights_policy,
            final_url=payload["effective_url"],
            staging_root=root,
            now=now,
        )
        if not validation.allowed:
            raise TranscriptImportError("post-fetch validation denied: " + validation.reason)
        material = extract_transcript_material(original, mime_type=mime_type)
        imported = writer.import_staged(
            request,
            candidate,
            receipt,
            provenance_extensions={
                "transcript_acquisition": {
                    "schema_version": "transcript-acquisition-audit/1",
                    "provider_payload_sha256": payload["provider_payload_sha256"],
                    "provider_extraction_version": payload["extraction_version"],
                    "effective_url": payload["effective_url"],
                    "http_status": payload["http_status"],
                    "retrieved_at": retrieved_at,
                    "rights_policy_sha256": validation.rights_policy_sha256,
                    "download_authorization_hash": authorization.receipt_hash,
                    "validated_actions": [
                        "automated_fetch",
                        "retain_original",
                        "derive_text",
                    ],
                    "derived_extractor_version": material.extractor_version,
                }
            },
        )
        if imported.source_id != material.original_source_id:
            raise TranscriptImportError("canonical source identity differs from transcript material")
        return TranscriptImportResult(
            canonical_import=imported,
            material=material,
            rights_policy_sha256=validation.rights_policy_sha256 or "",
            download_authorization_hash=authorization.receipt_hash,
            provider_payload_sha256=payload["provider_payload_sha256"],
            provider_extraction_version=payload["extraction_version"],
        )
    finally:
        if staged.exists():
            if staged.is_symlink() or staged.resolve(strict=True).parent != root.resolve(strict=True):
                raise TranscriptImportError("refusing to remove staged path outside allocated root")
            staged.unlink()


__all__ = [
    "MAX_PROVIDER_PAYLOAD_BYTES",
    "MAX_TOOL_RESULT_BYTES",
    "TRANSCRIPT_RESULT_SCHEMA",
    "TranscriptImportError",
    "TranscriptImportResult",
    "import_transcript_tool_result",
]
