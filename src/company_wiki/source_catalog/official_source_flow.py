"""Thin official-original registration, composing the existing catalog writer.

Only storage owns paths. Consumers receive SourceRef 2.0 and actual source
metadata; normalized evidence and finite summaries use the existing AUTO DAG.
"""

from __future__ import annotations
from dataclasses import asdict
from datetime import date, datetime, timezone
import hashlib
import json
import re
import tempfile
from pathlib import Path
from urllib.parse import urlsplit
from typing import Any

from .assertion_service import SOURCE_FACT_FIELDS
from .canonical_writer import CanonicalSourceWriter
from .document_kinds import SOURCE_FACT_KINDS
from .resolver import SourceRequest
from .metadata_observation import observe_metadata
from .source_reader import SourceVersionReader

IMPORT_REQUEST_SCHEMA = "official-source-import-request/1"
IMPORT_RESULT_SCHEMA = "official-source-import-result/1"
_MAX_BYTES = 128 * 1024 * 1024
_PPTX_MIME = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
_SUPPORTED_MIMES = {
    "application/pdf",
    "text/html",
    "application/xhtml+xml",
    "text/plain",
    "application/json",
    _PPTX_MIME,
}


class OfficialSourceError(ValueError):
    """Named source-data refusal, not another permission gate."""


def _text(value, field):
    if (
        not isinstance(value, str)
        or not value.strip()
        or value.strip() != value
        or len(value) > 2048
    ):
        raise OfficialSourceError("invalid_" + field)
    return value


def _metadata(value):
    if not isinstance(value, dict):
        raise OfficialSourceError("invalid_source_metadata")
    allowed = SOURCE_FACT_FIELDS | {"title", "publisher", "canonical_entity_id"}
    if not set(value) <= allowed:
        raise OfficialSourceError("unsupported_source_metadata_field")
    result = {**value}
    for field in ["entity", "document_kind", "title", "publisher", "source_url"]:
        result[field] = _text(value.get(field), field)
    if result["document_kind"] not in SOURCE_FACT_KINDS:
        raise OfficialSourceError("unknown_document_kind")
    url = urlsplit(result["source_url"])
    if (
        url.scheme not in {"http", "https"}
        or not url.hostname
        or url.username
        or url.password
    ):
        raise OfficialSourceError("invalid_source_url")
    for field in ["published_date", "filing_date", "period_end"]:
        item = result.get(field)
        if item is not None:
            try:
                if date.fromisoformat(item).isoformat() != item:
                    raise ValueError()
            except (ValueError, TypeError):
                raise OfficialSourceError("invalid_" + field) from None
        result[field] = item
    for field in ["market", "security_id", "fiscal_year", "fiscal_period", "language"]:
        result.setdefault(field, None)
    if result["market"] not in {None, "CN", "HK", "US"}:
        raise OfficialSourceError("invalid_market")
    if result["fiscal_year"] is not None and (
        type(result["fiscal_year"]) is not int
        or not 1900 <= result["fiscal_year"] <= 2200
    ):
        raise OfficialSourceError("invalid_fiscal_year")
    if result["language"] not in {None, "unknown", "en", "zh", "mixed"}:
        raise OfficialSourceError("invalid_language")
    for field in [
        "security_id",
        "fiscal_period",
        "provider_document_id",
        "canonical_entity_id",
        "provider",
    ]:
        if result.get(field) is not None:
            result[field] = _text(result[field], field)
    if result.get("security_id") is not None and not re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9.-]{0,19}", result["security_id"]
    ):
        raise OfficialSourceError("invalid_security_id")
    if result.get("provider") not in {None, "official"}:
        raise OfficialSourceError("invalid_provider")
    # Unknown is explicit: capture/event date never substitutes publication date.
    return result


def _validate_bytes(data, mime):
    if not data:
        raise OfficialSourceError("empty_original")
    if mime == "application/pdf":
        if not data.startswith(b"%PDF-"):
            raise OfficialSourceError("mime_mismatch")
        import fitz

        try:
            with fitz.open(stream=data, filetype="pdf") as doc:
                if doc.page_count < 1:
                    raise ValueError()
        except (RuntimeError, ValueError):
            raise OfficialSourceError("invalid_pdf") from None
    elif mime == _PPTX_MIME:
        _validate_presentation(data)
    elif mime in {"text/html", "application/xhtml+xml"}:
        from bs4 import BeautifulSoup

        try:
            text = data.decode("utf-8-sig")
        except UnicodeError:
            raise OfficialSourceError("invalid_html_encoding") from None
        soup = BeautifulSoup(text, "html.parser")
        if not soup.find(["html", "body", "article", "p", "h1", "table"]):
            raise OfficialSourceError("mime_mismatch")
        title = (soup.title.get_text(" ", strip=True) if soup.title else "").casefold()
        body = soup.get_text(" ", strip=True).casefold()
        error = {
            "access denied",
            "forbidden",
            "unauthorized",
            "not found",
            "just a moment",
            "service unavailable",
        }
        if title in error or (
            len(body) < 500 and any(body.startswith(t) for t in error)
        ):
            raise OfficialSourceError("response_is_error")
        if not body:
            raise OfficialSourceError("empty_original")
    elif mime in {"text/plain", "application/json"}:
        from .transcript_material import (
            extract_transcript_material,
            TranscriptMaterialError,
        )

        try:
            extract_transcript_material(data, mime_type=mime)
        except TranscriptMaterialError:
            raise OfficialSourceError("invalid_text_original") from None


def _validate_presentation(data):
    """Verify the bounded package, independent of narrative/OCR coverage."""
    import time
    import zipfile
    from company_wiki.document_normalization import normalize_document, NormalizationLimits
    from company_wiki.source_contract import source_id_for_sha256

    sha = hashlib.sha256(data).hexdigest()
    try:
        parsed = normalize_document(
            data, source_id=source_id_for_sha256(sha), source_sha256=sha,
            mime_type=_PPTX_MIME,
            limits=NormalizationLimits(max_source_bytes=_MAX_BYTES, deadline=time.monotonic() + 15),
        )
        if parsed.structure.page_count < 1:
            raise ValueError("empty or invalid presentation package")
    except (ValueError, zipfile.BadZipFile):
        raise OfficialSourceError("invalid_pptx") from None


def import_official_source(
    catalog, *, original: bytes, request: dict[str, Any]
) -> dict[str, Any]:
    """Register one bounded local/captured original; does not download or summarize."""
    if (
        not isinstance(request, dict)
        or request.get("schema_version") != IMPORT_REQUEST_SCHEMA
    ):
        raise OfficialSourceError("invalid_request_schema")
    if not isinstance(original, bytes):
        raise OfficialSourceError("invalid_original_bytes")
    _text(request.get("request_id"), "request_id")
    cap = request.get("max_bytes")
    if type(cap) is not int or not 0 < cap <= _MAX_BYTES:
        raise OfficialSourceError("invalid_byte_cap")
    if len(original) > cap:
        raise OfficialSourceError("source_byte_limit")
    sha = request.get("content_sha256")
    if (
        not isinstance(sha, str)
        or not re.fullmatch("[0-9a-f]{64}", sha)
        or hashlib.sha256(original).hexdigest() != sha
    ):
        raise OfficialSourceError("source_sha_mismatch")
    mime = request.get("mime_type")
    if mime not in _SUPPORTED_MIMES:
        raise OfficialSourceError("unsupported_mime")
    source = _metadata(request.get("source"))
    capture = request.get("capture_receipt")
    if (
        not isinstance(capture, dict)
        or capture.get("content_sha256") != sha
        or capture.get("response_bytes") != len(original)
    ):
        raise OfficialSourceError("capture_byte_identity_mismatch")
    if len(json.dumps(capture, ensure_ascii=False).encode()) > 16384:
        raise OfficialSourceError("capture_receipt_limit")
    for field in ["capture_method", "tool_name", "tool_call_id", "captured_at"]:
        _text(capture.get(field), field)
    try:
        dt = datetime.fromisoformat(capture["captured_at"].replace("Z", "+00:00"))
        if dt.tzinfo is None:
            raise ValueError()
    except (ValueError, TypeError):
        raise OfficialSourceError("invalid_capture_time") from None
    _validate_bytes(original, mime)
    writer = CanonicalSourceWriter(catalog)
    writer.staging_root.mkdir(parents=True, exist_ok=True)
    if writer.staging_root.is_symlink():
        raise OfficialSourceError("unsafe_staging_root")
    suffix = {
        "application/pdf": ".pdf",
        "text/html": ".html",
        "application/xhtml+xml": ".html",
        "text/plain": ".txt",
        "application/json": ".json",
        _PPTX_MIME: ".pptx",
    }[mime]
    fd, path = tempfile.mkstemp(
        prefix="official-", suffix=suffix, dir=writer.staging_root
    )
    staged = Path(path)
    try:
        with open(fd, "wb", closefd=True) as handle:
            handle.write(original)
        intent = SourceRequest(
            entity=source["entity"],
            document_kind=source["document_kind"],
            as_of_date=dt.date().isoformat(),
            market=source.get("market"),
            security_id=source.get("security_id"),
            fiscal_year=source.get("fiscal_year"),
            fiscal_period=source.get("fiscal_period"),
            language=source.get("language"),
        )
        result = writer.import_original_staged(
            request=intent,
            metadata=source,
            staged_path=staged,
            content_sha256=sha,
            byte_size=len(original),
            mime_type=mime,
            retrieved_at=dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            capture_receipt=capture,
        )
        if result.status.value == "imported_new":
            facts = {key: source[key] for key in SOURCE_FACT_FIELDS if key in source}
            facts["provider"] = "official"
            # These are stored capture declarations, not inferred business facts.
            # Keep independent publication and filing dates in the existing
            # source-facts projection; legacy scanner aliases prefer filing_date.
            evidence = {
                key: {
                    "locator": "canonical-provenance:/"
                    + ("company_name" if key == "entity" else key),
                    "value": value,
                }
                for key, value in facts.items()
            }
            catalog.record_source_facts(
                ref=result.source_ref, facts=facts, evidence=evidence
            )
        manifest = SourceVersionReader(catalog).describe_version(result.source_ref)
        if manifest.get("display_name") not in {None, source["entity"]}:
            raise OfficialSourceError("source_identity_conflict")
        stored = catalog.reader.exact_source_version(result.source_ref.document_id)
        persisted = observe_metadata(stored["metadata_json"]).metadata
        return {
            "schema_version": IMPORT_RESULT_SCHEMA,
            "status": "imported_new"
            if result.status.value == "imported_new"
            else "deduplicated",
            "source_ref": asdict(result.source_ref),
            "metadata": {
                **manifest,
                "entity": manifest.get("display_name") or source["entity"],
                "publisher": persisted.get("publisher"),
            },
            "capture_receipt": dict(capture),
            "download_events": 0,
        }
    finally:
        # This mkstemp is the only temporary object owned by this call.
        if staged.exists():
            if (
                staged.is_symlink()
                or staged.resolve().parent != writer.staging_root.resolve()
            ):
                raise OfficialSourceError("unsafe_staged_cleanup")
            staged.unlink()


def prepare_official_narrative_request(imports, *, batch_template):
    """Use caller/current-config settings; delegate all validation/ledger to AUTO."""
    from company_wiki.automation.narrative_batch_request import NarrativeBatchRequest

    value = dict(batch_template)
    value["sources"] = [item["source_ref"] for item in imports]
    return NarrativeBatchRequest.from_dict(value)
