"""Validate and canonically store one earnings-transcript tool result."""

from __future__ import annotations

import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .acquisition import DownloadCandidate, DownloadReceipt
from .canonical_writer import (
    CanonicalImportError,
    CanonicalImportResult,
    CanonicalSourceWriter,
)
from .resolver import SourceRequest
from .transcript_material import (
    TranscriptMaterial,
    TranscriptMaterialError,
    extract_transcript_material,
)
from .transcript_tool_contract import (
    MAX_PROVIDER_PAYLOAD_BYTES,
    MAX_TOOL_RESULT_BYTES,
    TranscriptToolContractError,
    parse_transcript_tool_result,
)


class TranscriptImportError(ValueError):
    """The tool result is invalid or cannot be safely stored as canonical raw."""


@dataclass(frozen=True)
class TranscriptImportResult:
    canonical_import: CanonicalImportResult
    material: TranscriptMaterial
    provider_payload_sha256: str
    provider_extraction_version: str


def _check_time(retrieved_at: str, now: str) -> None:
    try:
        retrieved = datetime.strptime(retrieved_at, "%Y-%m-%dT%H:%M:%SZ")
        checked = datetime.strptime(now, "%Y-%m-%dT%H:%M:%SZ")
    except (TypeError, ValueError) as exc:
        raise TranscriptImportError("invalid acquisition timestamp") from exc
    if retrieved > checked:
        raise TranscriptImportError("tool result retrieval time is in the future")


def _stage_original(
    writer: CanonicalSourceWriter, original: bytes, mime_type: str
) -> Path:
    root = writer.staging_root
    root.mkdir(parents=True, exist_ok=True)
    if not root.is_dir() or root.is_symlink():
        raise TranscriptImportError("allocated staging root is unsafe")
    suffix = ".txt" if mime_type == "text/plain" else ".html"
    fd, path_text = tempfile.mkstemp(prefix="transcript-", suffix=suffix, dir=root)
    with open(fd, "wb", closefd=True) as stream:
        stream.write(original)
        stream.flush()
    return Path(path_text)


def _remove_staged(staged: Path, root: Path) -> None:
    if not staged.exists():
        return
    if staged.is_symlink():
        raise TranscriptImportError("refusing to remove unsafe staged path")
    try:
        resolved = staged.resolve(strict=True)
        resolved.relative_to(root.resolve(strict=True))
    except (OSError, ValueError) as exc:
        raise TranscriptImportError("staged path escaped its temporary root") from exc
    resolved.unlink()


def import_transcript_tool_result(
    raw_result: bytes | str,
    *,
    request: SourceRequest,
    candidate: DownloadCandidate,
    writer: CanonicalSourceWriter,
    now: str,
) -> TranscriptImportResult:
    """Check source, period and bytes, then save the unchanged original once.

    The caller has already chosen the exact company and period and invoked the
    transcript provider. This importer needs no per-document authorization
    receipt or provider policy file; it still validates that the returned
    document matches that request and candidate before writing anything.
    """
    if not isinstance(request, SourceRequest):
        raise TranscriptImportError("request is required")
    if not isinstance(candidate, DownloadCandidate):
        raise TranscriptImportError("candidate is required")
    if not isinstance(writer, CanonicalSourceWriter):
        raise TranscriptImportError("canonical writer is required")
    if request.document_kind != "investor_call_transcript":
        raise TranscriptImportError("request is not for an earnings transcript")
    try:
        payload = parse_transcript_tool_result(
            raw_result,
            request=request,
            candidate=candidate,
            max_bytes=MAX_PROVIDER_PAYLOAD_BYTES,
        )
    except TranscriptToolContractError as exc:
        raise TranscriptImportError(str(exc)) from exc
    _check_time(payload.retrieved_at, now)
    try:
        material = extract_transcript_material(
            payload.original, mime_type=payload.mime_type
        )
    except TranscriptMaterialError as exc:
        raise TranscriptImportError(str(exc)) from exc
    if material.text_sha256 != payload.canonical_content_sha256:
        raise TranscriptImportError("canonical transcript text SHA-256 mismatch")
    if material.text_byte_size != payload.content_bytes:
        raise TranscriptImportError("canonical transcript text byte size mismatch")

    staged = _stage_original(writer, payload.original, payload.mime_type)
    receipt = DownloadReceipt(
        candidate_id=candidate.candidate_id,
        provider=candidate.provider,
        provider_document_id=candidate.provider_document_id,
        source_url=candidate.source_url,
        staged_path=str(staged),
        content_sha256=payload.provider_payload_sha256,
        byte_size=len(payload.original),
        mime_type=payload.mime_type,
        retrieved_at=payload.retrieved_at,
        http_status=payload.http_status,
        adapter_name=payload.adapter_name,
        adapter_version=payload.adapter_version,
        etag=candidate.etag,
        last_modified=candidate.last_modified,
    )
    try:
        imported = writer.import_staged(
            request,
            candidate,
            receipt,
            provenance_extensions={
                "transcript_acquisition": {
                    "schema_version": "transcript-acquisition-audit/2",
                    "provider_payload_sha256": payload.provider_payload_sha256,
                    "provider_extraction_version": payload.extraction_version,
                    "effective_url": payload.effective_url,
                    "http_status": payload.http_status,
                    "retrieved_at": payload.retrieved_at,
                    "derived_extractor_version": material.extractor_version,
                }
            },
        )
    except CanonicalImportError as exc:
        raise TranscriptImportError(str(exc)) from exc
    finally:
        if staged.exists():
            _remove_staged(staged, writer.staging_root)

    if imported.source_id != material.original_source_id:
        raise TranscriptImportError(
            "canonical source identity differs from original transcript bytes"
        )
    return TranscriptImportResult(
        canonical_import=imported,
        material=material,
        provider_payload_sha256=payload.provider_payload_sha256,
        provider_extraction_version=payload.extraction_version,
    )


__all__ = [
    "MAX_PROVIDER_PAYLOAD_BYTES",
    "MAX_TOOL_RESULT_BYTES",
    "TranscriptImportError",
    "TranscriptImportResult",
    "import_transcript_tool_result",
]
