"""Typed source subjects for official import request/2.

A source subject describes what a raw page is associated with.  It never
describes ownership: ``issuer_refs`` are associated subjects resolved by the
existing identity responsibilities, and a publisher, activity title, entity
hint or requested target company may not occupy an issuer slot.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

IMPORT_REQUEST_V2_SCHEMA = "official-source-import-request/2"
SUBJECT_KINDS = frozenset({"single_issuer", "multi_issuer_event", "unattributed"})
ATTRIBUTION_STATUSES = frozenset({"none", "partial", "full", "unknown"})
_ISSUER_REF_FIELDS = frozenset({
    "provider_company_id", "provider_activity_company_id", "stock_code",
    "company_name", "market", "security_id", "canonical_name",
})
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class SourceSubjectError(ValueError):
    """A named subject refusal."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class IssuerRef:
    provider_company_id: int | None = None
    provider_activity_company_id: int | None = None
    stock_code: str | None = None
    company_name: str | None = None
    market: str | None = None
    security_id: str | None = None
    canonical_name: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_company_id": self.provider_company_id,
            "provider_activity_company_id": self.provider_activity_company_id,
            "stock_code": self.stock_code,
            "company_name": self.company_name,
            "market": self.market,
            "security_id": self.security_id,
            "canonical_name": self.canonical_name,
        }


@dataclass(frozen=True)
class SourceSubject:
    kind: str
    attribution_status: str
    event_namespace: str | None = None
    event_id: str | None = None
    issuer_refs: tuple[IssuerRef, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "kind": self.kind,
            "attribution_status": self.attribution_status,
            "issuer_refs": [ref.to_dict() for ref in self.issuer_refs],
        }
        if self.kind == "multi_issuer_event":
            payload["event_namespace"] = self.event_namespace
            payload["event_id"] = self.event_id
        return payload


def _text(value: Any, code: str, *, limit: int = 512) -> str:
    if (not isinstance(value, str) or not value.strip() or value.strip() != value
            or len(value) > limit):
        raise SourceSubjectError(code)
    return value


def _optional_int(value: Any, code: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise SourceSubjectError(code)
    return value


def validate_source_subject(value: Any) -> SourceSubject:
    if not isinstance(value, dict):
        raise SourceSubjectError("invalid_source_subject")
    allowed = {"kind", "attribution_status", "event_namespace", "event_id",
               "issuer_refs"}
    if not set(value) <= allowed:
        raise SourceSubjectError("unsupported_source_subject_field")
    kind = value.get("kind")
    if kind not in SUBJECT_KINDS:
        raise SourceSubjectError("invalid_subject_kind")
    refs_value = value.get("issuer_refs", [])
    if not isinstance(refs_value, list):
        raise SourceSubjectError("invalid_issuer_refs")
    refs: list[IssuerRef] = []
    for item in refs_value:
        if not isinstance(item, dict) or not set(item) <= _ISSUER_REF_FIELDS:
            raise SourceSubjectError("invalid_issuer_ref")
        ref = IssuerRef(
            provider_company_id=_optional_int(
                item.get("provider_company_id"), "invalid_issuer_ref"),
            provider_activity_company_id=_optional_int(
                item.get("provider_activity_company_id"), "invalid_issuer_ref"),
            stock_code=item.get("stock_code"),
            company_name=item.get("company_name"),
            market=item.get("market"),
            security_id=item.get("security_id"),
            canonical_name=item.get("canonical_name"),
        )
        for name in ("stock_code", "company_name", "market", "security_id",
                     "canonical_name"):
            if getattr(ref, name) is not None:
                _text(getattr(ref, name), "invalid_issuer_ref")
        if (ref.provider_company_id is None
                and ref.provider_activity_company_id is None
                and not ref.stock_code and not ref.company_name
                and not ref.security_id and not ref.canonical_name):
            raise SourceSubjectError("issuer_ref_requires_identity")
        refs.append(ref)
    attribution = value.get("attribution_status")
    if kind == "unattributed":
        if refs:
            raise SourceSubjectError("unattributed_subject_has_no_issuers")
        attribution = "none"
    if kind == "single_issuer" and len(refs) != 1:
        raise SourceSubjectError("single_issuer_requires_one_ref")
    if attribution not in ATTRIBUTION_STATUSES:
        raise SourceSubjectError("invalid_attribution_status")
    namespace = event_id = None
    if kind == "multi_issuer_event":
        namespace = _text(value.get("event_namespace"), "invalid_event_namespace")
        event_id = _text(value.get("event_id"), "invalid_event_id")
    return SourceSubject(kind=kind, attribution_status=attribution,
                         event_namespace=namespace, event_id=event_id,
                         issuer_refs=tuple(refs))


@dataclass(frozen=True)
class ImportRequestV2:
    request_id: str
    max_bytes: int
    content_sha256: str
    mime_type: str
    source_subject: SourceSubject
    capture_receipt: dict[str, Any]
    document_kind: str = "other"
    expected_content_sha256: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "schema_version": IMPORT_REQUEST_V2_SCHEMA,
            "request_id": self.request_id,
            "max_bytes": self.max_bytes,
            "content_sha256": self.content_sha256,
            "mime_type": self.mime_type,
            "document_kind": self.document_kind,
            "source_subject": self.source_subject.to_dict(),
            "capture_receipt": dict(self.capture_receipt),
        }
        if self.expected_content_sha256 is not None:
            payload["expected_content_sha256"] = self.expected_content_sha256
        return payload


def validate_import_request_v2(value: Any) -> ImportRequestV2:
    if not isinstance(value, dict) or value.get("schema_version") != IMPORT_REQUEST_V2_SCHEMA:
        raise SourceSubjectError("invalid_request_schema")
    allowed = {"schema_version", "request_id", "max_bytes", "content_sha256",
               "mime_type", "source_subject", "capture_receipt",
               "expected_content_sha256", "document_kind"}
    if not set(value) <= allowed:
        raise SourceSubjectError("unsupported_request_field")
    request_id = value.get("request_id")
    if not isinstance(request_id, str) or not request_id.strip():
        raise SourceSubjectError("invalid_request_id")
    max_bytes = value.get("max_bytes")
    if (isinstance(max_bytes, bool) or not isinstance(max_bytes, int)
            or not 0 < max_bytes <= 128 * 1024 * 1024):
        raise SourceSubjectError("invalid_byte_cap")
    sha = value.get("content_sha256")
    if not isinstance(sha, str) or not _SHA256_RE.fullmatch(sha):
        raise SourceSubjectError("source_sha_mismatch")
    mime = value.get("mime_type")
    if mime not in {"application/json"}:
        raise SourceSubjectError("unsupported_mime")
    subject = validate_source_subject(value.get("source_subject"))
    document_kind = value.get("document_kind") or "other"
    if not isinstance(document_kind, str):
        raise SourceSubjectError("unknown_document_kind")
    receipt = value.get("capture_receipt")
    if not isinstance(receipt, dict):
        raise SourceSubjectError("invalid_capture_receipt")
    from .official_source_flow import _validate_capture_receipt
    _validate_capture_receipt(receipt, sha=sha)
    expected = value.get("expected_content_sha256")
    if expected is not None and (not isinstance(expected, str)
                                 or not _SHA256_RE.fullmatch(expected)):
        raise SourceSubjectError("invalid_expected_content_sha256")
    return ImportRequestV2(
        request_id=request_id, max_bytes=max_bytes, content_sha256=sha,
        mime_type=mime, source_subject=subject, capture_receipt=dict(receipt),
        document_kind=document_kind,
        expected_content_sha256=expected,
    )
