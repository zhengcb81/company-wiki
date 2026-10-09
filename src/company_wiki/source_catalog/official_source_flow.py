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
import os
import uuid
from urllib.parse import urlsplit
from typing import Any

from .assertion_service import SOURCE_FACT_FIELDS
from .canonical_writer import CanonicalSourceWriter, CanonicalImportError
from .acquisition_journal import AcquisitionJournal
from .lock import _acquisition_mutex
from .store import canonical_json
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
_CAPTURE_SUFFIXES = {"application/pdf": ".pdf", "text/html": ".html",
                     "application/xhtml+xml": ".html", "text/plain": ".txt",
                     "application/json": ".json", _PPTX_MIME: ".pptx"}


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
    if result["market"] is not None and (not isinstance(result["market"], str) or result["market"] not in {"CN", "HK", "US"}):
        raise OfficialSourceError("invalid_market")
    if result["fiscal_year"] is not None and (
        type(result["fiscal_year"]) is not int
        or not 1900 <= result["fiscal_year"] <= 2200
    ):
        raise OfficialSourceError("invalid_fiscal_year")
    if result["language"] is not None and (not isinstance(result["language"], str) or result["language"] not in {"unknown", "en", "zh", "mixed"}):
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


def _byte_cap(value):
    if type(value) is not int or not 0 < value <= _MAX_BYTES:
        raise OfficialSourceError("invalid_byte_cap")
    return value


def _validate_capture_receipt(capture, *, sha, byte_size=None):
    """Validate persisted observation shapes before reporting real capture/usage."""
    if (not isinstance(capture, dict) or capture.get("content_sha256") != sha
            or type(capture.get("response_bytes")) is not int
            or not 0 <= capture["response_bytes"] <= _MAX_BYTES
            or (byte_size is not None and capture["response_bytes"] != byte_size)):
        raise OfficialSourceError("capture_byte_identity_mismatch")
    try:
        encoded = json.dumps(capture, ensure_ascii=False, allow_nan=False).encode()
    except (TypeError, ValueError, RecursionError):
        raise OfficialSourceError("invalid_capture_receipt") from None
    if len(encoded) > 16384:
        raise OfficialSourceError("capture_receipt_limit")
    for field in ["capture_method", "tool_name", "tool_call_id", "captured_at"]:
        _text(capture.get(field), field)
    try:
        dt = datetime.fromisoformat(capture["captured_at"].replace("Z", "+00:00"))
        if dt.tzinfo is None:
            raise ValueError()
    except (ValueError, TypeError):
        raise OfficialSourceError("invalid_capture_time") from None
    if "http_status" in capture and (type(capture["http_status"]) is not int
                                     or not 100 <= capture["http_status"] <= 599):
        raise OfficialSourceError("invalid_capture_receipt")
    if "http_requests" in capture and (type(capture["http_requests"]) is not int
                                       or capture["http_requests"] < 0):
        raise OfficialSourceError("invalid_capture_receipt")
    for field in ("usage_complete", "provider_started"):
        if field in capture and type(capture[field]) is not bool:
            raise OfficialSourceError("invalid_capture_receipt")
    for field in ("acquisition_usage", "cumulative_acquisition_usage"):
        if field not in capture:
            continue
        usage = capture[field]
        if (not isinstance(usage, dict) or usage.get("schema_version") != "1.0"
                or type(usage.get("response_bytes")) is not int or usage["response_bytes"] < 0
                or not isinstance(usage.get("cost_usd"), str)):
            raise OfficialSourceError("invalid_capture_receipt")
        from decimal import Decimal, InvalidOperation
        try:
            cost = Decimal(usage["cost_usd"])
            if not cost.is_finite() or cost < 0:
                raise ValueError()
        except (InvalidOperation, ValueError):
            raise OfficialSourceError("invalid_capture_receipt") from None
    return dt


def _validate_import_header(request):
    if not isinstance(request, dict) or request.get("schema_version") != IMPORT_REQUEST_SCHEMA:
        raise OfficialSourceError("invalid_request_schema")
    _text(request.get("request_id"), "request_id")
    _byte_cap(request.get("max_bytes"))
    sha = request.get("content_sha256")
    if not isinstance(sha, str) or not re.fullmatch("[0-9a-f]{64}", sha):
        raise OfficialSourceError("source_sha_mismatch")
    mime = request.get("mime_type")
    if not isinstance(mime, str) or mime not in _SUPPORTED_MIMES:
        raise OfficialSourceError("unsupported_mime")
    source = _metadata(request.get("source"))
    expected = request.get("expected_content_sha256")
    if expected is not None and (not isinstance(expected, str) or not re.fullmatch("[0-9a-f]{64}", expected)):
        raise OfficialSourceError("invalid_expected_content_sha256")
    return source


def _validate_import_request(original, request):
    source = _validate_import_header(request)
    if not isinstance(original, bytes):
        raise OfficialSourceError("invalid_original_bytes")
    if len(original) > request["max_bytes"]:
        raise OfficialSourceError("source_byte_limit")
    if hashlib.sha256(original).hexdigest() != request["content_sha256"]:
        raise OfficialSourceError("source_sha_mismatch")
    dt = _validate_capture_receipt(request.get("capture_receipt"),
                                   sha=request["content_sha256"], byte_size=len(original))
    return source, dt


def _staging_root(catalog):
    configured = catalog.config.catalog_dir / "staging"
    if configured.is_symlink():
        raise OfficialSourceError("unsafe_staging_root")
    writer = CanonicalSourceWriter(catalog)
    if len(str(writer.staging_root).encode("utf-16-le")) // 2 + 1 + 45 > 259:
        raise OfficialSourceError("staging_root_path_limit")
    writer.staging_root.mkdir(parents=True, exist_ok=True)
    if writer.staging_root.is_symlink():
        raise OfficialSourceError("unsafe_staging_root")
    return writer.staging_root


def _persist_capture(catalog, original, request, *, complete=True):
    """Persist bytes and their immutable actual observation before import.

    These two staging objects are recovery material, not another task queue.
    Failed outcomes are discoverable in the existing AcquisitionJournal; a
    crash before journaling is still discoverable from the capture sidecar.
    """
    root = _staging_root(catalog)
    capture_id = uuid.uuid4().hex
    suffix = _CAPTURE_SUFFIXES[request["mime_type"]]
    staged = root / (capture_id + suffix)
    descriptor = root / (capture_id + ".capture.json")
    state = {"schema_version": "official-source-retained-capture/1",
             "capture_id": capture_id, "staged_name": staged.name, "request": request,
             "complete": complete}
    if len(str(descriptor).encode("utf-16-le")) // 2 > 259:
        raise OfficialSourceError("staging_root_path_limit")
    # Write-once names avoid adoption/cleanup of another call's originals.
    try:
        with staged.open("xb") as stream:
            stream.write(original)
            stream.flush()
            os.fsync(stream.fileno())
        with descriptor.open("x", encoding="utf-8") as stream:
            stream.write(canonical_json(state) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
    except Exception as primary:
        # If the receipt's own storage fails, retain the raw bytes and expose
        # the named incomplete recovery material; never pretend it is replayable.
        primary.capture_id = capture_id
        primary.capture_receipt = dict(request["capture_receipt"])
        try:
            _journal(catalog, state, outcome="failed", reason="capture_persistence_failed",
                     error_type=type(primary).__name__, canonical_path=str(staged.resolve()),
                     error=canonical_json({"capture_id": capture_id,
                                           "capture_receipt": request["capture_receipt"]}))
        except Exception as journal_error:
            primary.add_note("capture journal failed: " + type(journal_error).__name__)
        raise
    return staged, descriptor, state


def _journal(catalog, state, *, outcome, reason=None, error_type=None, canonical_path=None, error=None):
    request = state["request"]
    source = request["source"]
    return AcquisitionJournal(catalog.config.catalog_dir).record(
        request_id=request["request_id"], outcome=outcome,
        adapter_name="official-original-import", provider="official",
        provider_document_id=source.get("provider_document_id"), source_url=source["source_url"],
        content_sha256=request["content_sha256"],
        canonical_path=canonical_path, reason=reason, error_type=error_type, error=error,
    )


def _import_retained(catalog, staged, descriptor, state, *, bytes_validated=False, max_bytes=None):
    request = state["request"]
    try:
        if not state.get("complete", True):
            raise OfficialSourceError("incomplete_capture_requires_new_request")
        cap = request["max_bytes"] if max_bytes is None else min(request["max_bytes"], _byte_cap(max_bytes))
        with staged.open("rb") as stream:
            original = stream.read(cap + 1)
        if len(original) > cap:
            raise OfficialSourceError("source_byte_limit")
        source, dt = _validate_import_request(original, request)
        if request.get("expected_content_sha256") not in {None, request["content_sha256"]}:
            raise OfficialSourceError("source_sha_mismatch")
        if not bytes_validated:
            _validate_bytes(original, request["mime_type"])
        status = request["capture_receipt"].get("http_status")
        if status is not None and not 200 <= status < 300:
            raise OfficialSourceError("response_is_error")
        # Byte identity and fact corrections compose the existing source API.
        facts = {key: source[key] for key in SOURCE_FACT_FIELDS if key in source}
        facts["provider"] = "official"
        sha = request["content_sha256"]
        evidence = {key: {"locator": "official-import-declaration:/" + key,
                          "value": value, "content_sha256": sha}
                    for key, value in facts.items()}
        from company_wiki.source_contract import source_id_for_sha256
        from .source_reader import SourceRef, SourceReadError
        from .assertion_service import restore_document_facts
        from .local_inventory import observe_document
        source_id = source_id_for_sha256(sha)
        document_id = source_id.replace("urn:company-wiki:source:", "urn:company-wiki:document:")
        existing = (catalog.reader.exact_source_version(document_id)
                    if catalog.config.database_path.exists() else None)
        if existing is not None:
            ref = SourceRef(document_id, source_id, sha, len(original), request["mime_type"])
            if existing["source_status"] == "active":
                manifest = SourceVersionReader(catalog).describe_version(ref)
                if manifest.get("display_name") not in {None, source["entity"]}:
                    raise OfficialSourceError("source_identity_conflict")
            else:
                try:
                    restore_document_facts(catalog, ref=ref, facts=facts, evidence=evidence,
                                           retirement_observation=observe_document(catalog, document_id))
                except SourceReadError as exc:
                    raise OfficialSourceError(exc.reason) from exc
        intent = SourceRequest(entity=source["entity"], document_kind=source["document_kind"],
                               as_of_date=dt.date().isoformat(), market=source.get("market"),
                               security_id=source.get("security_id"), fiscal_year=source.get("fiscal_year"),
                               fiscal_period=source.get("fiscal_period"), language=source.get("language"))
        writer = CanonicalSourceWriter(catalog)
        result = writer.import_original_staged(
            request=intent, metadata=source, staged_path=staged, content_sha256=sha,
            byte_size=len(original), mime_type=request["mime_type"],
            retrieved_at=dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            capture_receipt=request["capture_receipt"], cleanup_staged=False,
        )
        catalog.record_source_facts(ref=result.source_ref, facts=facts, evidence=evidence)
        manifest = SourceVersionReader(catalog).describe_version(result.source_ref)
        if manifest.get("display_name") not in {None, source["entity"]}:
            raise OfficialSourceError("source_identity_conflict")
        stored = catalog.reader.exact_source_version(result.source_ref.document_id)
        persisted = observe_metadata(stored["metadata_json"]).metadata
        out = {"schema_version": IMPORT_RESULT_SCHEMA,
               "status": "imported_new" if result.status.value == "imported_new" else "deduplicated",
               "source_ref": asdict(result.source_ref),
               "metadata": {**manifest, "entity": manifest.get("display_name") or source["entity"],
                            "publisher": persisted.get("publisher")},
               "capture_receipt": dict(request["capture_receipt"]), "download_events": 0}
        captured_http = request["capture_receipt"].get("capture_method") == "bounded_http"
        outcome = (("downloaded_new" if captured_http else "imported_original")
                   if result.status.value == "imported_new" else
                   ("deduplicated_after_download" if captured_http else "deduplicated_original"))
        attempt = _journal(catalog, state, outcome=outcome, canonical_path=result.canonical_path)
        _persist_completed(catalog, state, out, journal_attempt_id=attempt.attempt_id)
        # A durable result must survive a lost response before raw cleanup.
        writer._remove_staged(staged)
        descriptor.unlink()
        return out
    except Exception as primary:
        primary.capture_id = state["capture_id"]
        primary.capture_receipt = dict(request["capture_receipt"])
        try:
            _journal(catalog, state, outcome="failed", reason="official_import_failed",
                     error_type=type(primary).__name__, canonical_path=str(staged.resolve()))
        except Exception as journal_error:
            primary.add_note("capture journal failed: " + type(journal_error).__name__)
        raise


def import_official_source(catalog, *, original: bytes, request: dict[str, Any]) -> dict[str, Any]:
    """Register local verified original, retaining it if immutable commit fails."""
    _validate_import_request(original, request)
    _validate_bytes(original, request["mime_type"])
    staged, descriptor, state = _persist_capture(catalog, original, request)
    return _import_retained(catalog, staged, descriptor, state, bytes_validated=True)


def _capture_id(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{32}", value):
        raise OfficialSourceError("invalid_capture_id")
    return value


def _read_capture_record(path, *, error_code):
    if path.is_symlink():
        raise OfficialSourceError("unsafe_retained_capture")
    with path.open("rb") as stream:
        raw = stream.read(65537)
    if len(raw) > 65536:
        raise OfficialSourceError("capture_receipt_limit")
    def unique_pairs(items):
        value = {}
        for key, item in items:
            if key in value:
                raise ValueError()
            value[key] = item
        return value
    def invalid_constant(_):
        raise ValueError()
    try:
        state = json.loads(raw, object_pairs_hook=unique_pairs, parse_constant=invalid_constant)
        if not isinstance(state, dict):
            raise ValueError()
    except (ValueError, UnicodeError, RecursionError):
        raise OfficialSourceError(error_code) from None
    return state


def _load_retained(catalog, capture_id, *, require_original=True):
    _capture_id(capture_id)
    root = _staging_root(catalog)
    descriptor = root / (capture_id + ".capture.json")
    if not descriptor.is_file():
        raise OfficialSourceError("retained_capture_receipt_unavailable")
    state = _read_capture_record(descriptor, error_code="invalid_retained_capture")
    name = state.get("staged_name")
    try:
        if (state.get("schema_version") != "official-source-retained-capture/1"
                or state.get("capture_id") != capture_id or type(state.get("complete", True)) is not bool
                or not isinstance(name, str)
                or not re.fullmatch(capture_id + r"\.[a-z0-9]{1,10}", name)):
            raise OfficialSourceError("invalid_retained_capture")
        _validate_import_header(state.get("request"))
        request = state["request"]
        _validate_capture_receipt(request.get("capture_receipt"), sha=request["content_sha256"])
        if name != capture_id + _CAPTURE_SUFFIXES[request["mime_type"]]:
            raise OfficialSourceError("invalid_retained_capture")
    except OfficialSourceError:
        raise OfficialSourceError("invalid_retained_capture") from None
    staged = root / name
    if (staged.is_symlink() or (require_original and not staged.is_file())
            or (staged.exists() and not staged.is_file())):
        raise OfficialSourceError("retained_original_unavailable")
    return staged, descriptor, state


def _persist_completed(catalog, state, out, *, journal_attempt_id):
    """Bounded capture-output projection, linked to the existing success journal.

    No body, paths, queue or permission is copied here. Persistence occurs
    before deleting recoverable raw; a failed result write retains the input.
    Same-ID recovery uses the existing OS file mutex around result lookup/import.
    """
    root = _staging_root(catalog)
    record = {"schema_version": "official-source-completed-capture/1",
              "capture_id": state["capture_id"], "journal_attempt_id": journal_attempt_id,
              "source_ref": out["source_ref"], "status": out["status"],
              "max_bytes": state["request"]["max_bytes"],
              "capture_receipt": out["capture_receipt"]}
    encoded = canonical_json(record).encode("utf-8")
    if len(encoded) > 65536:
        raise OfficialSourceError("capture_receipt_limit")
    temporary = root / (uuid.uuid4().hex + ".result.tmp")
    completed = root / (state["capture_id"] + ".result.json")
    created = False
    try:
        with temporary.open("xb") as stream:
            created = True
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, completed)
    except Exception as primary:
        if created:
            try:
                temporary.unlink(missing_ok=True)
            except OSError as cleanup_error:
                primary.add_note("completion projection cleanup failed: " + type(cleanup_error).__name__)
        raise


def _replay_completed(catalog, capture_id, *, max_bytes=None):
    from .source_reader import SourceRef
    from company_wiki.source_contract import source_id_for_sha256
    path = _staging_root(catalog) / (capture_id + ".result.json")
    if not path.exists() and not path.is_symlink():
        return None
    record = _read_capture_record(path, error_code="invalid_completed_capture")
    try:
        value = record.get("source_ref")
        if (record.get("schema_version") != "official-source-completed-capture/1"
                or record.get("capture_id") != capture_id
                or not isinstance(record.get("status"), str)
                or record["status"] not in {"imported_new", "deduplicated"}
                or not isinstance(record.get("journal_attempt_id"), str)
                or not re.fullmatch(r"urn:company-wiki:acquisition-attempt:sha256:[0-9a-f]{64}", record["journal_attempt_id"])
                or not isinstance(value, dict)
                or set(value) != {"schema_version", "document_id", "source_id", "content_sha256", "byte_size", "mime_type"}):
            raise OfficialSourceError("invalid_completed_capture")
        sha = value["content_sha256"]
        if (not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{64}", sha)
                or value["schema_version"] != "2.0"
                or value["source_id"] != source_id_for_sha256(sha)
                or value["document_id"] != value["source_id"].replace("urn:company-wiki:source:", "urn:company-wiki:document:")
                or type(value["byte_size"]) is not int or not 0 < value["byte_size"] <= _MAX_BYTES
                or not isinstance(value["mime_type"], str) or value["mime_type"] not in _SUPPORTED_MIMES):
            raise OfficialSourceError("invalid_completed_capture")
        cap = _byte_cap(record.get("max_bytes"))
        _validate_capture_receipt(record.get("capture_receipt"), sha=sha, byte_size=value["byte_size"])
    except OfficialSourceError:
        raise OfficialSourceError("invalid_completed_capture") from None
    if max_bytes is not None:
        cap = min(cap, _byte_cap(max_bytes))
    if value["byte_size"] > cap:
        raise OfficialSourceError("source_byte_limit")
    ref = SourceRef(**value)
    reader = SourceVersionReader(catalog)
    # Current storage/byte verification is owned by the public reader, streaming
    # SHA without copying the source body into another output or persisted file.
    reader.verify_version(ref, purpose="filing_reuse")
    manifest = reader.describe_version(ref)
    stored = catalog.reader.exact_source_version(ref.document_id)
    persisted = observe_metadata(stored["metadata_json"]).metadata
    out = {"schema_version": IMPORT_RESULT_SCHEMA, "status": record["status"],
           "source_ref": asdict(ref),
           "metadata": {**manifest, "entity": manifest.get("display_name"),
                        "publisher": persisted.get("publisher")},
           "capture_receipt": dict(record["capture_receipt"]), "download_events": 0,
           "acquisition_usage": {"schema_version": "1.0", "response_bytes": 0, "cost_usd": "0"}}
    cleanup = _cleanup_completed_staging(catalog, capture_id, record)
    if cleanup is not None:
        out["staging_cleanup"] = cleanup
    return out


def _cleanup_completed_staging(catalog, capture_id, record):
    """Resume only this exact capture after current canonical/cap verification.

    The same-ID mutex is held by recovery. Canonical source/result remain
    available if a safe staging diagnostic is needed. Unknown/changed raw is
    never adopted or deleted merely because its UUID matches a completed ID.
    """
    try:
        root = _staging_root(catalog)
        descriptor = root / (capture_id + ".capture.json")
        ref = record["source_ref"]
        if not descriptor.exists() and not descriptor.is_symlink():
            raw = root / (capture_id + _CAPTURE_SUFFIXES[ref["mime_type"]])
            if raw.exists() or raw.is_symlink():
                return {"status": "retained", "reason": "retained_capture_receipt_unavailable"}
            return None
        staged, descriptor, state = _load_retained(catalog, capture_id, require_original=False)
        request = state["request"]
        if (not state.get("complete", True)
                or request["content_sha256"] != ref["content_sha256"]
                or request["mime_type"] != ref["mime_type"]
                or request["max_bytes"] != record["max_bytes"]
                or request["capture_receipt"] != record["capture_receipt"]):
            return {"status": "retained", "reason": "retained_capture_identity_mismatch"}
        if staged.exists():
            # Bounded streaming identity check: retain no copy of a large body.
            before = staged.stat()
            digest = hashlib.sha256()
            size = 0
            remaining = ref["byte_size"] + 1
            with staged.open("rb") as stream:
                while remaining:
                    chunk = stream.read(min(65536, remaining))
                    if not chunk:
                        break
                    size += len(chunk)
                    digest.update(chunk)
                    remaining -= len(chunk)
            after = staged.stat()
            if (size != ref["byte_size"] or digest.hexdigest() != ref["content_sha256"]
                    or (before.st_size, before.st_mtime_ns, before.st_ino)
                    != (after.st_size, after.st_mtime_ns, after.st_ino)):
                return {"status": "retained", "reason": "retained_capture_identity_mismatch"}
            CanonicalSourceWriter(catalog)._remove_staged(staged)
        # Raw can already be gone after interrupted descriptor cleanup.
        descriptor.unlink(missing_ok=True)
        return None
    except OfficialSourceError as exc:
        allowed = {"invalid_retained_capture", "unsafe_retained_capture",
                   "retained_original_unavailable", "retained_capture_receipt_unavailable",
                   "capture_receipt_limit", "unsafe_staging_root", "staging_root_path_limit"}
        reason = str(exc) if str(exc) in allowed else "invalid_retained_capture"
        return {"status": "retained", "reason": reason}
    except CanonicalImportError:
        return {"status": "retained", "reason": "staging_cleanup_failed", "error_type": "CanonicalImportError"}
    except OSError:
        return {"status": "retained", "reason": "staging_cleanup_failed", "error_type": "OSError"}


def list_retained_official_captures(catalog):
    """Store-owned staging inventory; never exposes storage paths downstream."""
    result = []
    for descriptor in sorted(_staging_root(catalog).glob("*.capture.json")):
        capture_id = descriptor.name.removesuffix(".capture.json")
        try:
            staged, _, state = _load_retained(catalog, capture_id)
            request = state["request"]
            complete = state.get("complete", True)
            result.append({"capture_id": capture_id, "request_id": request["request_id"],
                           ("content_sha256" if complete else "captured_partial_sha256"): request["content_sha256"],
                           "byte_size": staged.stat().st_size,
                           "status": "retained" if complete else "incomplete"})
        except (OSError, ValueError, KeyError):
            result.append({"capture_id": capture_id, "status": "unavailable"})
    seen = {row["capture_id"] for row in result}
    for staged in sorted(_staging_root(catalog).iterdir()):
        capture_id = staged.stem
        if re.fullmatch(r"[0-9a-f]{32}", capture_id) and staged.is_file() and capture_id not in seen:
            result.append({"capture_id": capture_id, "byte_size": staged.stat().st_size,
                           "status": "receipt_unavailable"})
    return result


def recover_official_source(catalog, *, capture_id, max_bytes=None):
    """Resume/replay the exact capture, checking the optional current byte cap."""
    _capture_id(capture_id)
    if max_bytes is not None:
        _byte_cap(max_bytes)
    root = _staging_root(catalog)
    # Reuse the existing file mutex; the .r suffix keeps its Win32 name bounded
    # and distinct from captured raw or recovery records in inventory.
    with _acquisition_mutex(root / (capture_id + ".r")):
        replay = _replay_completed(catalog, capture_id, max_bytes=max_bytes)
        if replay is not None:
            return replay
        out = _import_retained(catalog, *_load_retained(catalog, capture_id), max_bytes=max_bytes)
        out["acquisition_usage"] = {"schema_version": "1.0", "response_bytes": 0, "cost_usd": "0"}
        return out


def capture_official_source(catalog, *, request, budget=None, transport=None):
    """One configured original capture under shared byte/cost/total-time budget.

    Async socket operations are actually cancelable, including slow trickles;
    this is not a coroutine around a blocking sync HTTP reader. No auto retry.
    The request optionally pins known bytes for zero-GET verified local reuse.
    """
    import asyncio
    import httpx
    from .bounded_http import BudgetedAsyncHTTPTransport, ProviderBudgetStop, usage_receipt
    from .download_budget import AcquisitionBudget
    if not isinstance(request, dict) or request.get("schema_version") != "official-source-capture-request/1":
        raise OfficialSourceError("invalid_capture_request_schema")
    source = _metadata(request.get("source"))
    _text(request.get("request_id"), "request_id")
    cap, seconds = request.get("max_bytes"), request.get("max_seconds")
    if (type(cap) is not int or not 0 < cap <= _MAX_BYTES or isinstance(seconds, bool)
            or not isinstance(seconds, (int, float)) or not 0 < seconds <= 300):
        raise OfficialSourceError("invalid_capture_limits")
    mime = request.get("mime_type")
    if not isinstance(mime, str) or mime not in _SUPPORTED_MIMES:
        raise OfficialSourceError("unsupported_mime")
    expected = request.get("expected_content_sha256")
    if expected is not None and (not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected)):
        raise OfficialSourceError("invalid_expected_content_sha256")
    if budget is None:
        budget = AcquisitionBudget.from_limits(max_response_bytes=cap, max_seconds=seconds,
                                               max_cost_usd=request.get("max_cost_usd", "0"))
    if not isinstance(budget, AcquisitionBudget):
        raise TypeError("budget must be AcquisitionBudget")
    if expected is not None:
        path = CanonicalSourceWriter(catalog)._existing_original(expected)
        if path is not None:
            with path.open("rb") as stream:
                original = stream.read(cap + 1)
            capture = {"capture_method": "verified_local_reuse", "tool_name": "company-wiki-official-source",
                       "tool_call_id": "reuse-" + uuid.uuid4().hex,
                       "captured_at": datetime.now(timezone.utc).isoformat(),
                       "response_bytes": len(original), "content_sha256": expected}
            local = {"schema_version": IMPORT_REQUEST_SCHEMA, "request_id": request["request_id"],
                     "source": source, "mime_type": mime, "content_sha256": expected,
                     "max_bytes": cap, "capture_receipt": capture}
            out = import_official_source(catalog, original=original, request=local)
            out["acquisition_usage"] = {"schema_version": "1.0", "response_bytes": 0, "cost_usd": "0"}
            return out
        # Captured bytes can exist before catalog registration succeeds. Resume
        # their immutable observation rather than making a redundant GET.
        for retained in list_retained_official_captures(catalog):
            if retained.get("status") == "retained" and retained.get("content_sha256") == expected:
                _, _, state = _load_retained(catalog, retained["capture_id"])
                if state["request"]["source"]["entity"] != source["entity"]:
                    raise OfficialSourceError("source_identity_conflict")
                out = recover_official_source(catalog, capture_id=retained["capture_id"], max_bytes=cap)
                out["acquisition_usage"] = {"schema_version": "1.0", "response_bytes": 0, "cost_usd": "0"}
                return out
    _staging_root(catalog)  # The existing journal also needs its configured parent.
    before = budget.response_bytes_used
    cost_before = budget.cost_usd_used
    def operation_usage():
        return {"schema_version": "1.0", "response_bytes": budget.response_bytes_used - before,
                "cost_usd": str(budget.cost_usd_used - cost_before)}
    capture = {"capture_method": "bounded_http", "tool_name": "company-wiki-official-source",
               "tool_call_id": "http-" + uuid.uuid4().hex, "http_requests": 0,
               "started_at": datetime.now(timezone.utc).isoformat()}
    partial = bytearray()
    class CountedTransport(httpx.AsyncBaseTransport):
        def __init__(self, inner):
            self.inner = inner
        async def handle_async_request(self, http_request):
            capture["http_requests"] += 1
            budget.observe_provider(started=True, complete=True)
            return await self.inner.handle_async_request(http_request)
        async def aclose(self):
            await self.inner.aclose()
    async def fetch():
        inner = CountedTransport(transport or httpx.AsyncHTTPTransport(retries=0))
        async with httpx.AsyncClient(transport=BudgetedAsyncHTTPTransport(inner, budget),
                                     follow_redirects=True, max_redirects=5, trust_env=False) as client:
            async with client.stream("GET", source["source_url"]) as response:
                capture.update(http_status=response.status_code, effective_url=str(response.url),
                               response_mime_type=response.headers.get("content-type", "").split(";")[0].strip().lower())
                async for chunk in response.aiter_bytes():
                    partial.extend(chunk)
                    if len(partial) > cap:
                        raise ProviderBudgetStop("byte_budget_exceeded", "source byte limit exceeded")
                return bytes(partial)
    async def bounded():
        try:
            return await asyncio.wait_for(fetch(), timeout=min(seconds, budget.remaining_seconds))
        except asyncio.TimeoutError as exc:
            raise ProviderBudgetStop("deadline_exceeded", "acquisition deadline exceeded") from exc
    try:
        budget.ensure_new_request()
        original = asyncio.run(bounded())
    except Exception as primary:
        started = capture["http_requests"] > 0
        complete = not started
        budget.observe_provider(started=started, complete=complete)
        primary.acquisition_usage = operation_usage()
        primary.acquisition_usage_complete = complete
        primary.provider_started = started
        failed_receipt = {**capture, "captured_at": datetime.now(timezone.utc).isoformat(),
                          "response_bytes": len(partial), "content_sha256": hashlib.sha256(partial).hexdigest(),
                          "usage_complete": complete, "acquisition_usage": primary.acquisition_usage}
        primary.capture_receipt = failed_receipt
        failed_request = {"schema_version": IMPORT_REQUEST_SCHEMA, "request_id": request["request_id"],
                          "source": source, "mime_type": mime, "content_sha256": failed_receipt["content_sha256"],
                          "max_bytes": cap, "capture_receipt": failed_receipt}
        try:
            staged, _, state = _persist_capture(catalog, bytes(partial), failed_request, complete=False)
            primary.capture_id = state["capture_id"]
            _journal(catalog, state, outcome="failed", reason=getattr(primary, "error_code", "http_failed"),
                     error_type=type(primary).__name__, canonical_path=str(staged.resolve()),
                     error=canonical_json({"acquisition_usage": primary.acquisition_usage,
                                           "provider_started": started, "usage_complete": complete}))
        except Exception as receipt_error:
            primary.add_note("capture recovery persistence failed: " + type(receipt_error).__name__)
        raise
    sha = hashlib.sha256(original).hexdigest()
    capture.update(captured_at=datetime.now(timezone.utc).isoformat(), response_bytes=len(original),
                   content_sha256=sha, usage_complete=True,
                   acquisition_usage=operation_usage(), cumulative_acquisition_usage=usage_receipt(budget))
    local = {"schema_version": IMPORT_REQUEST_SCHEMA, "request_id": request["request_id"],
             "source": source, "mime_type": mime, "content_sha256": sha,
             "max_bytes": cap, "capture_receipt": capture}
    if expected is not None:
        local["expected_content_sha256"] = expected
    state = None
    try:
        staged, descriptor, state = _persist_capture(catalog, original, local)
        if expected is not None and expected != sha:
            _journal(catalog, state, outcome="failed", reason="source_sha_mismatch",
                     error_type="OfficialSourceError", canonical_path=str(staged.resolve()))
            raise OfficialSourceError("source_sha_mismatch")
        out = _import_retained(catalog, staged, descriptor, state)
    except Exception as primary:
        if state is not None:
            primary.capture_id = state["capture_id"]
        primary.capture_receipt = capture
        primary.acquisition_usage = capture["acquisition_usage"]
        primary.acquisition_usage_complete = True
        primary.provider_started = True
        raise
    out["download_events"] = 1
    out["acquisition_usage"] = capture["acquisition_usage"]
    return out


def prepare_official_narrative_request(imports, *, batch_template):
    """Use caller/current-config settings; delegate all validation/ledger to AUTO."""
    from company_wiki.automation.narrative_batch_request import NarrativeBatchRequest

    value = dict(batch_template)
    value["sources"] = [item["source_ref"] for item in imports]
    return NarrativeBatchRequest.from_dict(value)
