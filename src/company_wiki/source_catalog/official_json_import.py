"""Official JSON import (request/2): typed subjects, shared raw, typed layout.

Valid grammar lands in the catalog as a shared source-oriented raw page.
Unknown-but-legal layouts are stored with ``unsupported_layout`` status and
never become business evidence.  Invalid pages keep their retained capture
and journal entry without being indexed.
"""

from __future__ import annotations

from dataclasses import asdict
import hashlib
from typing import Any
from urllib.parse import urlsplit
from unicodedata import category

from .canonical_writer import CanonicalSourceWriter
from .document_kinds import SOURCE_FACT_KINDS
from .official_json_layout import (
    OfficialJsonLayoutError,
    describe_layout_page,
    registered_layout_ids,
)
from .official_json_structure import (
    JsonStructureError,
    JsonStructureLimits,
    parse_json_structure,
)
from .official_json_subject import (
    SourceSubjectError,
    validate_import_request_v2,
)
from .official_source_flow import (
    OfficialSourceError,
    _attach_capture_http_observation,
    _journal,
    _persist_capture,
)

IMPORT_RESULT_V2_SCHEMA = "official-source-import-result/2"
_LAYOUT_STATUS_PARSED = "parsed"
_LAYOUT_STATUS_UNSUPPORTED = "unsupported_layout"

# Structural admission defaults follow the investigation proposal; callers
# may pass tighter limits per request/deployment ceiling.
DEFAULT_JSON_LIMITS = JsonStructureLimits()


def recognize_layout(doc) -> tuple[str | None, str, str]:
    """Try registered layouts in deterministic order; never guess shapes."""
    for layout_id in registered_layout_ids():
        try:
            observation = describe_layout_page(layout_id, doc)
        except OfficialJsonLayoutError:
            continue
        return layout_id, _LAYOUT_STATUS_PARSED, observation.envelope_status
    return None, _LAYOUT_STATUS_UNSUPPORTED, "unknown"


def import_official_json_source(catalog, *, original: bytes, request: dict[str, Any],
                                limits: JsonStructureLimits | None = None) -> dict[str, Any]:
    """Register one official JSON page through the public /2 contract."""
    try:
        validated = validate_import_request_v2(request)
    except SourceSubjectError as exc:
        raise OfficialSourceError(exc.code) from exc
    if not isinstance(original, (bytes, bytearray)):
        raise OfficialSourceError("invalid_original_bytes")
    original = bytes(original)
    if len(original) > validated.max_bytes:
        raise OfficialSourceError("source_byte_limit")
    if hashlib.sha256(original).hexdigest() != validated.content_sha256:
        raise OfficialSourceError("source_sha_mismatch")
    expected = validated.expected_content_sha256
    if expected is not None and expected != validated.content_sha256:
        raise OfficialSourceError("source_sha_mismatch")

    def retained_failure(reason: str, error_type: str, receipt: dict) -> OfficialSourceError:
        staged, descriptor, state = _persist_capture(
            catalog, original, validated.to_dict())
        error = OfficialSourceError(reason)
        error.capture_id = state["capture_id"]
        error.capture_receipt = dict(receipt)
        try:
            _journal(catalog, state, outcome="failed", reason=reason,
                     error_type=error_type, canonical_path=str(staged.resolve()))
        except Exception as journal_error:  # pragma: no cover - best effort
            error.add_note("capture journal failed: " + type(journal_error).__name__)
        return error

    # Grammar admission happens before any catalog effect; refusals keep the
    # actual capture for recovery instead of discarding observed bytes.
    try:
        doc = parse_json_structure(
            original, limits=limits or DEFAULT_JSON_LIMITS)
    except JsonStructureError as exc:
        raise retained_failure(exc.code, "JsonStructureError",
                               validated.capture_receipt) from exc

    layout_id, layout_status, envelope_status = recognize_layout(doc)
    if envelope_status == "response_is_error":
        # An error response stays an observation, never indexed business data.
        raise retained_failure("response_is_error", "OfficialSourceError",
                               validated.capture_receipt)

    staged, descriptor, state = _persist_capture(
        catalog, original, validated.to_dict())
    try:
        result = _commit_shared(catalog, staged, state, validated,
                                layout_id=layout_id, layout_status=layout_status,
                                original=original)
    except Exception as primary:
        setattr(primary, "capture_id", state["capture_id"])
        setattr(primary, "capture_receipt", dict(validated.capture_receipt))
        _attach_capture_http_observation(primary, validated.capture_receipt)
        try:
            _journal(catalog, state, outcome="failed", reason="official_json_import_failed",
                     error_type=type(primary).__name__,
                     canonical_path=str(staged.resolve()))
        except Exception as journal_error:  # pragma: no cover
            primary.add_note("capture journal failed: " + type(journal_error).__name__)
        raise
    writer = CanonicalSourceWriter(catalog)
    writer._remove_staged(staged)
    descriptor.unlink()
    return result


def _commit_shared(catalog, staged, state, validated, *, layout_id, layout_status,
                   original: bytes) -> dict[str, Any]:
    from .official_json_layout import layout_fingerprint
    document_kind = validated.document_kind
    if document_kind not in SOURCE_FACT_KINDS:
        raise OfficialSourceError("unknown_document_kind")
    subject = validated.source_subject
    event_label = None
    if subject.kind == "multi_issuer_event":
        event_label = f"{subject.event_namespace}:{subject.event_id}"
    provenance_extensions = {
        "official_capture": dict(validated.capture_receipt),
        "official_source_subject": subject.to_dict(),
    }
    if layout_id is not None:
        provenance_extensions["official_json_layout"] = {
            "layout_id": layout_id,
            "layout_status": layout_status,
            "layout_fingerprint": layout_fingerprint(layout_id),
        }
    writer = CanonicalSourceWriter(catalog)
    result = writer.import_shared_original_staged(
        request_id=validated.request_id,
        document_kind=document_kind,
        title=event_label or "official shared JSON page",
        source_url=_captured_source_url(validated.capture_receipt),
        publisher="official",
        staged_path=staged,
        content_sha256=validated.content_sha256,
        byte_size=len(original),
        mime_type=validated.mime_type,
        retrieved_at=_captured_at_utc(validated.capture_receipt),
        capture_receipt=validated.capture_receipt,
        provenance_extensions=provenance_extensions,
        cleanup_staged=False,
    )
    attempt = _journal(catalog, state,
                       outcome=("imported_original" if result.status.value == "imported_new"
                                else "deduplicated_original"),
                       canonical_path=result.canonical_path)
    out = {
        "schema_version": IMPORT_RESULT_V2_SCHEMA,
        "status": "imported_new" if result.status.value == "imported_new" else "deduplicated",
        "source_ref": asdict(result.source_ref),
        "source_subject": subject.to_dict(),
        "layout": {
            "layout_id": layout_id,
            "parse_status": layout_status,
            **({"layout_fingerprint": layout_fingerprint(layout_id)}
               if layout_id is not None else {}),
        },
        "capture_receipt": dict(validated.capture_receipt),
        "download_events": 0,
    }
    from .official_source_flow import _persist_completed
    _persist_completed(catalog, state, out, journal_attempt_id=attempt.attempt_id)
    return out


def _captured_source_url(receipt: dict[str, Any]) -> str | None:
    """Project the observed original URL, without inventing source facts.

    Existing captures carry ``url``. A later local import may retain that
    observation under ``original_capture_observation``; it belongs to this
    page only when its byte identity matches the validated outer capture.
    Missing/invalid observations remain unknown and never block raw storage.
    """
    observation = receipt
    if "url" not in observation:
        original = receipt.get("original_capture_observation")
        if not isinstance(original, dict) or (
            original.get("content_sha256") != receipt["content_sha256"]
            or original.get("response_bytes") != receipt["response_bytes"]
        ):
            return None
        observation = original
    url = observation.get("url")
    if (not isinstance(url, str) or not url or len(url) > 2048
            or any(char.isspace() or category(char) == "Cc" for char in url)):
        return None
    try:
        parts = urlsplit(url)
        if (parts.scheme not in {"https", "http"} or not parts.hostname
                or parts.username or parts.password):
            return None
        parts.port  # Validate a declared port without any network operation.
    except ValueError:
        return None
    return url


def _captured_at_utc(receipt: dict[str, Any]) -> str:
    from datetime import datetime, timezone
    raw = str(receipt.get("captured_at") or "")
    stamp = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    return stamp.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def import_official_json_staged(catalog, staged, descriptor, state) -> dict[str, Any]:
    """Recovery entry: finish a retained /2 capture from staging."""
    request = state["request"]
    try:
        validated = validate_import_request_v2(request)
    except SourceSubjectError as exc:
        raise OfficialSourceError(exc.code) from exc
    cap = request["max_bytes"]
    with staged.open("rb") as stream:
        original = stream.read(cap + 1)
    if len(original) > cap:
        raise OfficialSourceError("source_byte_limit")
    if hashlib.sha256(original).hexdigest() != validated.content_sha256:
        raise OfficialSourceError("source_sha_mismatch")
    try:
        doc = parse_json_structure(original, limits=DEFAULT_JSON_LIMITS)
    except JsonStructureError as exc:
        raise OfficialSourceError(exc.code) from exc
    layout_id, layout_status, envelope_status = recognize_layout(doc)
    if envelope_status == "response_is_error":
        raise OfficialSourceError("response_is_error")
    result = _commit_shared(catalog, staged, state, validated,
                            layout_id=layout_id, layout_status=layout_status,
                            original=original)
    result["acquisition_usage"] = {"schema_version": "1.0", "response_bytes": 0,
                                   "cost_usd": "0"}
    CanonicalSourceWriter(catalog)._remove_staged(staged)
    descriptor.unlink()
    return result
