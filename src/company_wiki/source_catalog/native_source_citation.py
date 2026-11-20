"""Read one immutable original and route its citation and issuer independently."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from company_wiki.document_model.citation_locator import (
    CitationBlock,
    match_native_citation,
    native_paragraphs,
    native_pdf_pages,
)
from company_wiki.source_contract.source_version import VerifiedContent, VerifiedVersionReceipt

from .cn_primary_issuer import MAX_BYTES as PDF_MAX_BYTES
from .cn_primary_issuer import PrimaryIssuerUnavailable, extract_cn_issuer, pdf_text_pages
from .document_browse_projection import document_version_id
from .issuer_identity import (
    ISSUER_NAMESPACE_SEC_CIK,
    ISSUER_VERIFIER_HK_SOURCE_FACTS,
    ISSUER_VERIFIER_SEC_DEI,
    official_hk_source_issuer,
)
from .source_reader import SourceReadError, SourceRef, SourceVersionReader


def _published_ref(ref: SourceRef, observation: VerifiedContent | VerifiedVersionReceipt) -> dict[str, Any]:
    return {
        "source_ref": ref.to_dict(),
        "document_version_id": document_version_id(ref.document_id, ref.source_id, ref.content_sha256),
        "current_byte_verification": {
            "content_sha256": observation.content_sha256, "byte_size": observation.byte_size,
            "source_read_policy_sha256": observation.source_read_policy_sha256,
            "read_at": observation.read_at,
        },
    }


class NativeCitationUnavailable(ValueError):
    """A source may remain readable while its citation parser is unavailable."""


def _native_limit(mime: str) -> int:
    if mime == "application/pdf":
        return PDF_MAX_BYTES
    try:
        from company_wiki.document_normalization import DEFAULT_LIMITS, UnsupportedFormatError, normalization_identity
    except ImportError as exc:
        raise NativeCitationUnavailable("native_citation_parser_unavailable") from exc
    try:
        normalization_identity(mime)
    except UnsupportedFormatError as exc:
        raise NativeCitationUnavailable("native_citation_format_unsupported") from exc
    return DEFAULT_LIMITS.max_source_bytes


def _native_document_blocks(original: VerifiedContent, mime: str) -> Iterable[CitationBlock]:
    from company_wiki.document_normalization import NormalizationError, normalize_verified_document

    try:
        document = normalize_verified_document(original, mime_type=mime)
    except NormalizationError as exc:
        raise NativeCitationUnavailable("native_citation_parse_unavailable") from exc
    return native_paragraphs(document.units)


def _owner_issuer(
    catalog, ref: SourceRef, original: VerifiedContent, metadata: dict[str, Any], pages: list[str] | None,
) -> dict[str, Any]:
    facts = catalog.browse_source_facts(ref.source_id)
    market = metadata.get("market")
    if facts is not None and facts.verified_ref == ref and facts.issuer_facts is not None:
        hk = official_hk_source_issuer(facts.issuer_facts)
        if hk is not None:
            official = facts.issuer_facts
            ticker = hk.value.split(":", 1)[0]
            return {
                "state": "verified", "verifier": ISSUER_VERIFIER_HK_SOURCE_FACTS,
                "key": {"namespace": hk.namespace, "value": hk.value},
                "source_ref": ref.to_dict(), "assertion_id": facts.assertion_id,
                "security": {
                    "market": "HK", "ticker": ticker, "exchange": "SEHK", "security_id": ticker,
                    "source_name": official.provider,
                    "source_record_id": official.provider_document_id or official.source_url,
                },
            }
    if market == "CN" and pages is not None:
        try:
            return extract_cn_issuer(catalog, ref, pages=pages, metadata=metadata)
        except PrimaryIssuerUnavailable as exc:
            return {"state": "unavailable", "reason": exc.reason}
    if market == "HK":
        return {"state": "unavailable", "reason": "official_listing_source_unverified"}
    if market != "US" or facts is None or facts.verified_ref != ref or facts.evidence_basis != "source-facts":
        return {"state": "unavailable", "reason": "original_issuer_facts_unavailable"}

    from .assertion_service import source_scope_qualification

    try:
        qualification = source_scope_qualification(catalog, ref, metadata=metadata, issuer_only=True)
        if qualification is None:
            return {"state": "unavailable", "reason": "issuer_namespace_unsupported_for_document"}
        primary = qualification.verify_primary_scope(original.data)
    except SourceReadError as exc:
        state = "conflict" if exc.reason == "primary_issuer_conflict" else "unavailable"
        return {"state": state, "reason": exc.reason}
    identity = qualification.identity
    security_id = getattr(identity, "security_id", None) or metadata.get("security_id")
    return {
        "state": "verified", "verifier": ISSUER_VERIFIER_SEC_DEI,
        "key": {"namespace": ISSUER_NAMESPACE_SEC_CIK, "value": str(int(primary["cik"]))},
        "source_ref": ref.to_dict(), "assertion_id": facts.assertion_id,
        "security": {
            "market": "US", "ticker": getattr(identity, "ticker", security_id),
            "exchange": getattr(identity, "exchange", None), "security_id": security_id,
            "source_name": "sec", "source_record_id": identity.source_record_id,
        },
    }


def read_native_citation(
    catalog, ref: SourceRef, *, quote: str | None = None, locator: dict[str, Any] | None = None,
    include_issuer: bool = False,
) -> dict[str, Any]:
    """Verify source bytes once. A citation miss leaves the original available."""
    reader = SourceVersionReader(catalog)
    has_evidence = quote is not None or locator is not None
    mime = ref.mime_type.split(";", 1)[0].strip().lower()
    if not has_evidence and not include_issuer:
        return _published_ref(ref, reader.verify_version(ref, purpose="source_export"))
    try:
        if ref.byte_size > _native_limit(mime):
            raise NativeCitationUnavailable("native_citation_source_byte_limit")
    except NativeCitationUnavailable as exc:
        receipt = reader.verify_version(ref, purpose="source_export")
        result = _published_ref(ref, receipt)
        if has_evidence:
            result["evidence_validation"] = {"state": "unavailable", "reason": str(exc)}
        return result

    original, metadata = reader.open_described_version(ref, purpose="source_export")
    result = _published_ref(ref, original)
    result["published_date"] = metadata.get("published_date")
    pages = None
    try:
        if mime == "application/pdf":
            pages = pdf_text_pages(original.data)
        if has_evidence:
            blocks = native_pdf_pages(pages) if pages is not None else _native_document_blocks(original, mime)
            validation = match_native_citation(blocks, quote=quote, locator=locator)
            if pages is not None:
                pointer = validation.get("locator")
                validation["physical_page"] = int(pointer["value"]) if pointer else None
            result["evidence_validation"] = validation
    except (PrimaryIssuerUnavailable, NativeCitationUnavailable) as exc:
        if has_evidence:
            result["evidence_validation"] = {
                "state": "unavailable",
                "reason": exc.reason if isinstance(exc, PrimaryIssuerUnavailable) else str(exc),
            }
    if include_issuer:
        result["issuer_proof"] = _owner_issuer(catalog, ref, original, metadata, pages)
    return result
